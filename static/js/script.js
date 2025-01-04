document.addEventListener('DOMContentLoaded', function () {
    const recordButtonText = document.getElementById('recordButtonText'); // Updated reference to Record text
    const stopButton = document.getElementById('stopButton');
    const userInput = document.getElementById('user_input');
    const userForm = document.getElementById('userForm');

    let isRecording = false;

    // Add click event to the Record text
    recordButtonText.addEventListener('click', function () {
        if (!isRecording) {
            startRecording();
        }
    });

    stopButton.addEventListener('click', function () {
        stopRecording();
    });

    function startRecording() {
        isRecording = true;
        recordButtonText.style.backgroundColor = '#ff6b6b'; // Highlight during recording
        recordButtonText.style.cursor = 'not-allowed'; // Disable further clicks
        recordButtonText.textContent = 'Recording...';

        fetch('/start_listening', {
            method: 'POST',
        })
            .then((response) => response.json())
            .then((data) => {
                isRecording = false;
                resetRecordButton();

                if (data.text && data.text !== 'Could not understand audio') {
                    userInput.value = data.text;
                } else {
                    alert('Speech not recognized. Please try again.');
                }
            })
            .catch((error) => {
                console.error('Error:', error);
                isRecording = false;
                resetRecordButton();
            });
    }

    function stopRecording() {
        if (isRecording) {
            isRecording = false;
            resetRecordButton();
        }
    }

    function resetRecordButton() {
        recordButtonText.style.backgroundColor = '#e84118'; // Reset to original color
        recordButtonText.style.cursor = 'pointer'; // Re-enable clicking
        recordButtonText.textContent = 'Record'; // Reset text
    }

    userForm.addEventListener('submit', function (e) {
        e.preventDefault();

        const customerName = document.getElementById('customer_name').value;
        const userInputText = userInput.value;

        fetch('/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                customer_name: customerName,
                user_input: userInputText,
            }),
        })
            .then((response) => response.json())
            .then((data) => {
                document.getElementById('sentiment').textContent =
                    `Sentiment: ${data.sentiment.sentiment} (Polarity: ${data.sentiment.polarity})`;
                document.getElementById('response').textContent =
                    `AI Response: ${data.llama_response}`;
            })
            .catch((error) => console.error('Error:', error));
    });
});
