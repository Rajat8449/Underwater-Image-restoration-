
from __future__ import print_function, division,absolute_import
## python libs
import os
import numpy as np
import random
import fnmatch
import numpy as np
from PIL import Image

import tensorflow as tf
import keras.backend as K
from keras.models import Model
from keras.optimizers import Adam
from keras.layers import Input, Dropout, Concatenate
from keras.layers import BatchNormalization, Activation
from keras.layers import LeakyReLU
from keras.layers.convolutional import UpSampling2D, Conv2D


class CycleGAN():
    def __init__(self, imrow=256, imcol=256, imchan=3):
        ## input image shape
        self.img_rows, self.img_cols, self.channels = imrow, imcol, imchan
        self.img_shape = (self.img_rows, self.img_cols, self.channels)

        ## input images and their conditioning images
        img_A = Input(shape=self.img_shape)
        img_B = Input(shape=self.img_shape)

        # Calculate output shape of D (PatchGAN)
        patch = int(self.img_rows / 2**4)
        self.disc_patch = (patch, patch, 1)

        # Number of filters in the first layer of G and D
        self.gf = 32
        self.df = 64

        # Loss weights
        self.lambda_cycle = 10.0 # Cycle-consistency loss
        self.lambda_id = 0.1 * self.lambda_cycle   # Identity loss

        optimizer = Adam(0.0002, 0.5)

        # Build and compile the discriminators
        self.d_A = self.CycleGAN_discriminator()
        self.d_B = self.CycleGAN_discriminator()
        self.d_A.compile(loss='mse', optimizer=optimizer, metrics=['accuracy'])
        self.d_B.compile(loss='mse', optimizer=optimizer, metrics=['accuracy'])

        # Build the generators
        self.g_AB = self.CycleGAN_generator()
        self.g_BA = self.CycleGAN_generator()

        # Translate images to the other domain
        fake_B = self.g_AB(img_A)
        fake_A = self.g_BA(img_B)

        # Translate images back to original domain
        reconstr_A = self.g_BA(fake_B)
        reconstr_B = self.g_AB(fake_A)

        # Identity mapping of images
        img_A_id = self.g_BA(img_A)
        img_B_id = self.g_AB(img_B)

        # For the combined model we will only train the generators
        self.d_A.trainable = False
        self.d_B.trainable = False

        # Discriminators determines validity of translated images
        valid_A = self.d_A(fake_A)
        valid_B = self.d_B(fake_B)

        # Combined model trains generators to fool discriminators
        self.combined = Model(inputs=[img_A, img_B],
                              outputs=[ valid_A, valid_B,reconstr_A, reconstr_B, img_A_id, img_B_id ])
        self.combined.compile(loss=['mse', 'mse','mae', 'mae','mae', 'mae'],
                              loss_weights=[1, 1,self.lambda_cycle, self.lambda_cycle, self.lambda_id, self.lambda_id ],
                              optimizer=optimizer)



    def CycleGAN_generator(self):
        """U-Net Generator"""

        def conv2d(layer_input, filters, f_size=4):
            """Layers used during downsampling"""
            d = Conv2D(filters, kernel_size=f_size, strides=2, padding='same')(layer_input)
            d = LeakyReLU(alpha=0.2)(d)
            d = BatchNormalization(momentum=0.8)(d)
            return d

        def deconv2d(layer_input, skip_input, filters, f_size=4, dropout_rate=0):
            """Layers used during upsampling"""
            u = UpSampling2D(size=2)(layer_input)
            u = Conv2D(filters, kernel_size=f_size, strides=1, padding='same', activation='relu')(u)
            if dropout_rate:
                u = Dropout(dropout_rate)(u)
            u = BatchNormalization(momentum=0.8)(u)
            u = Concatenate()([u, skip_input])
            return u

        # Image input
        d0 = Input(shape=self.img_shape)

        # Downsampling
        d1 = conv2d(d0, self.gf)
        d2 = conv2d(d1, self.gf*2)
        d3 = conv2d(d2, self.gf*4)
        d4 = conv2d(d3, self.gf*8)

        # Upsampling
        u1 = deconv2d(d4, d3, self.gf*4)
        u2 = deconv2d(u1, d2, self.gf*2)
        u3 = deconv2d(u2, d1, self.gf)

        u4 = UpSampling2D(size=2)(u3)
        output_img = Conv2D(self.channels, kernel_size=4, strides=1, padding='same', activation='tanh')(u4)

        return Model(d0, output_img)



    def CycleGAN_discriminator(self):

        def d_layer(layer_input, filters, f_size=4, normalization=True):
            """Discriminator layer"""
            d = Conv2D(filters, kernel_size=f_size, strides=2, padding='same')(layer_input)
            d = LeakyReLU(alpha=0.2)(d)
            if normalization:
                d = BatchNormalization(momentum=0.8)(d)
            return d

        img = Input(shape=self.img_shape)

        d1 = d_layer(img, self.df, normalization=False)
        d2 = d_layer(d1, self.df*2)
        d3 = d_layer(d2, self.df*4)
        d4 = d_layer(d3, self.df*8)

        validity = Conv2D(1, kernel_size=4, strides=1, padding='same')(d4)

        return Model(img, validity)

def deprocess(x, np_uint8=True):
    # [-1,1] -> [0, 255]
    x = (x+1.0)*127.5
    return np.uint8(x) if np_uint8 else x

def preprocess(x):
    # [0,255] -> [-1, 1]
    return (x/127.5)-1.0

def augment(a_img, b_img):
    """
       Augment images - a is distorted
    """
    # randomly interpolate
    a = random.random()
    a_img = a_img*(1-a) + b_img*a
    # flip image left right
    if (random.random() < 0.25):
        a_img = np.fliplr(a_img)
        b_img = np.fliplr(b_img)
    # flip image up down
    if (random.random() < 0.25):
        a_img = np.flipud(a_img)
        b_img = np.flipud(b_img)
    return a_img, b_img

def getPaths(data_dir):
    exts = ['*.png','*.PNG','*.jpg','*.JPG', '*.JPEG']
    image_paths = []
    for pattern in exts:
        for d, s, fList in os.walk(data_dir):
            for filename in fList:
                if (fnmatch.fnmatch(filename, pattern)):
                    fname_ = os.path.join(d,filename)
                    image_paths.append(fname_)
    return np.asarray(image_paths)

def read_and_resize(path, img_res):
    im = Image.open(path).resize(img_res)
    if im.mode=='L':
        copy = np.zeros((res[1], res[0], 3))
        copy[:, :, 0] = im
        copy[:, :, 1] = im
        copy[:, :, 2] = im
        im = copy
    return np.array(im).astype(np.float32)

def read_and_resize_pair(pathA, pathB, img_res):
    img_A = read_and_resize(pathA, img_res)
    img_B = read_and_resize(pathB, img_res)
    return img_A, img_B

def get_local_test_data(data_dir, img_res=(256, 256)):
    assert os.path.exists(data_dir), "local image path doesnt exist"
    imgs = []
    for p in getPaths(data_dir):
        img = read_and_resize(p, img_res)
        imgs.append(img)
    imgs = preprocess(np.array(imgs))
    return imgs

class DataLoader():
    def __init__(self, data_dir, dataset_name, img_res=(256, 256), test_only=False):
        self.img_res = img_res
        self.DATA = dataset_name
        self.data_dir = data_dir
        if not test_only:
            self.trainA_paths = getPaths(os.path.join(self.data_dir, "trainA")) # distorted
            self.trainB_paths = getPaths(os.path.join(self.data_dir, "trainB")) # enhanced
            if (len(self.trainA_paths)<len(self.trainB_paths)):
                self.trainB_paths = self.trainB_paths[:len(self.trainA_paths)]
            elif (len(self.trainA_paths)>len(self.trainB_paths)):
                self.trainA_paths = self.trainA_paths[:len(self.trainB_paths)]
            else: pass
            self.val_paths = getPaths(os.path.join(self.data_dir, "validation"))
            self.num_train, self.num_val = len(self.trainA_paths), len(self.val_paths)
            print ("{0} training pairs\n".format(self.num_train))
        else:
            self.test_paths    = getPaths(os.path.join(self.data_dir, "test"))
            print ("{0} test images\n".format(len(self.test_paths)))

    def get_test_data(self, batch_size=1):
        idx = np.random.choice(np.arange(len(self.test_paths)), batch_size, replace=False)
        paths = self.test_paths[idx]
        imgs = []
        for p in paths:
            img = read_and_resize(p, self.img_res)
            imgs.append(img)
        imgs = preprocess(np.array(imgs))
        return imgs

    def load_val_data(self, batch_size=1):
        idx = np.random.choice(np.arange(self.num_val), batch_size, replace=False)
        pathsA = self.trainA_paths[idx]
        pathsB = self.trainB_paths[idx]
        imgs_A, imgs_B = [], []
        for idx in range(len(pathsB)):
            img_A, img_B = read_and_resize_pair(pathsA[idx], pathsB[idx], self.img_res)
            imgs_A.append(img_A)
            imgs_B.append(img_B)
        imgs_A = preprocess(np.array(imgs_A))
        imgs_B = preprocess(np.array(imgs_B))
        return imgs_A, imgs_B

    def load_batch(self, batch_size=1, data_augment=True):
        self.n_batches = self.num_train//batch_size
        for i in range(self.n_batches-1):
            batch_A = self.trainA_paths[i*batch_size:(i+1)*batch_size]
            batch_B = self.trainB_paths[i*batch_size:(i+1)*batch_size]
            imgs_A, imgs_B = [], []
            for idx in range(len(batch_A)):
                img_A, img_B = read_and_resize_pair(batch_A[idx], batch_B[idx], self.img_res)
                if (data_augment):
                    img_A, img_B = augment(img_A, img_B)
                imgs_A.append(img_A)
                imgs_B.append(img_B)
            imgs_A = preprocess(np.array(imgs_A))
            imgs_B = preprocess(np.array(imgs_B))
            yield imgs_A, imgs_B

if __name__=="__main__":
    # for testing the initialization
    funie_gan = CycleGAN()