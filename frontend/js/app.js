const apigClient = apigClientFactory.newClient({
    apiKey: 'PvaLBkwzy1273pu0hMZOncEC8JbwgjV8QVNtjhn2'
});

document.addEventListener('DOMContentLoaded', () => {
    const searchButton = document.getElementById('search-button');
    const uploadButton = document.getElementById('upload-button');

    searchButton.addEventListener('click', handleSearch);
    uploadButton.addEventListener('click', handleUpload);
});

async function handleSearch() {
    const query = document.getElementById('search-input').value;
    try {
        const response = await apigClient.searchGet({q: query});
        displayResults(response.data);
    } catch (error) {
        console.error('Error searching photos:', error);
        alert('Error searching photos');
    }
}

function displayResults(results) {
    const resultsSection = document.getElementById('results-section');
    resultsSection.innerHTML = '';
    if (results && results.length > 0) {
        results.forEach(photo => {
            const imgContainer = document.createElement('div');
            imgContainer.className = 'img-container';
            
            const img = document.createElement('img');
            img.src = photo;
            console.log(photo)
            // img.alt = photo.labels.join(', ');
            
            // const labels = document.createElement('p');
            // labels.textContent = `Labels: ${photo.labels.join(', ')}`;
            
            imgContainer.appendChild(img);
            // imgContainer.appendChild(labels);
            resultsSection.appendChild(imgContainer);
        });
    } else {
        resultsSection.innerHTML = '<p>No results found</p>';
    }
}

async function handleUpload() {
    const file = document.getElementById('photo-upload').files[0];
    const customLabels = document.getElementById('custom-labels').value;
    
    if (!file) {
        alert('Please select a file to upload');
        return;
    }

    function getBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => {
                let encoded = reader.result.replace(/^data:(.*;base64,)?/, '');
                if (encoded.length % 4 > 0) {
                    encoded += '='.repeat(4 - (encoded.length % 4));
                }
                resolve(encoded);
            };
            reader.onerror = (error) => reject(error);
        });
    }

    try {
        const encodedImage = await getBase64(file);
        const response = await apigClient.uploadFilenamePut(
            {
                filename: file.name,
                'Content-Type': file.type + ';base64',
                'customlabels': customLabels
            },
            encodedImage,
            {
                headers: {
                    'Content-Type': file.type + ';base64',
                    'customlabels': customLabels
                }
            }
        );

        if (response.status === 200) {
            alert('Photo uploaded successfully!');
        } else {
            throw new Error('Upload failed');
        }
    } catch (error) {
        console.error('Error uploading photo:', error);
        alert('Error uploading photo');
    }
}