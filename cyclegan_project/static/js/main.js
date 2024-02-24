function processImage() {
    var inputImage = document.getElementById('inputImage');
    var inputImageDisplay = document.getElementById('inputImageDisplay');
    var outputImageDisplay = document.getElementById('outputImageDisplay');
    var inputImageContainer = document.getElementById('inputImageContainer');
    var outputImageContainer = document.getElementById('outputImageContainer');
    
    var formData = new FormData();
    formData.append('input_image', inputImage.files[0]);
    
    fetch('/process_image', {
        method: 'POST',
        body: formData,
    })
    .then(response => response.json())
    .then(data => {
        inputImageDisplay.src = data.input_image_url;
        outputImageDisplay.src = data.translated_image_url;
        inputImageContainer.style.display = 'block';
        outputImageContainer.style.display = 'block';
    });
}
