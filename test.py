# A web interface for Whisper that allows you to upload audio files and get the transcript.
# Run uvicorn test:app --reload

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import whisper
import tempfile
import os

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    return '''
        <html>
            <head>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        background-color: #f5f5f5;
                        margin: 0;
                        padding: 20px;
                    }
                    .container {
                        max-width: 800px;
                        margin: 0 auto;
                        background: white;
                        padding: 40px;
                        border-radius: 10px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        text-align: center;
                    }
                    .drop-zone {
                        width: 100%;
                        height: 200px;
                        border: 2px dashed #4CAF50;
                        border-radius: 5px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        flex-direction: column;
                        cursor: pointer;
                        margin: 20px 0;
                        transition: border 0.3s ease;
                    }
                    .drop-zone:hover {
                        border-color: #45a049;
                    }
                    .drop-zone.dragover {
                        background-color: rgba(76, 175, 80, 0.1);
                    }
                    .drop-zone p {
                        color: #666;
                        margin: 10px 0;
                    }
                    .submit-btn {
                        background-color: #4CAF50;
                        color: white;
                        padding: 12px 24px;
                        border: none;
                        border-radius: 5px;
                        cursor: pointer;
                        font-size: 16px;
                        transition: background-color 0.3s ease;
                    }
                    .submit-btn:hover {
                        background-color: #45a049;
                    }
                    #file-name {
                        margin-top: 10px;
                        color: #666;
                    }
                    .record-container {
                        margin: 20px 0;
                        padding: 20px;
                        border: 1px solid #ddd;
                        border-radius: 10px;
                    }
                    
                    .record-button {
                        background-color: #ff4444;
                        color: white;
                        padding: 12px 24px;
                        border: none;
                        border-radius: 50px;
                        cursor: pointer;
                        font-size: 16px;
                        transition: all 0.3s ease;
                    }
                    
                    .record-button.recording {
                        animation: pulse 1.5s infinite;
                    }
                    
                    .record-button.active {
                        transform: scale(0.95);
                        transition: transform 0.1s;
                    }
                    
                    @keyframes pulse {
                        0% { transform: scale(1); }
                        50% { transform: scale(1.05); }
                        100% { transform: scale(1); }
                    }
                    
                    .spinner {
                        display: none;
                        width: 80px;
                        height: 80px;
                        margin: 20px auto;
                    }
                    
                    .transcription-container {
                        margin-top: 20px;
                        text-align: left;
                        padding: 20px;
                        background: #f9f9f9;  /* Light grey background */
                        border-radius: 5px;
                    }
                    
                    .transcription-entry {
                        position: relative;
                        margin: 10px 0;
                        padding: 15px;
                        background: white;  /* Keep entries white for contrast */
                        border-radius: 5px;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                        opacity: 0;
                        transform: translateY(20px);
                        transition: all 0.3s ease;
                    }
                    
                    .transcription-entry.show {
                        opacity: 1;
                        transform: translateY(0);
                    }
                    
                    /* Toggle switch styles */
                    .toggle-container {
                        margin: 20px 0;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        gap: 20px;
                    }
                    
                    .toggle-switch {
                        position: relative;
                        display: inline-block;
                        width: 60px;
                        height: 34px;
                    }
                    
                    .toggle-switch input {
                        opacity: 0;
                        width: 0;
                        height: 0;
                    }
                    
                    .toggle-slider {
                        position: absolute;
                        cursor: pointer;
                        top: 0;
                        left: 0;
                        right: 0;
                        bottom: 0;
                        background-color: #4CAF50;
                        transition: .4s;
                        border-radius: 34px;
                    }
                    
                    .toggle-slider:before {
                        position: absolute;
                        content: "";
                        height: 26px;
                        width: 26px;
                        left: 4px;
                        bottom: 4px;
                        background-color: white;
                        transition: .4s;
                        border-radius: 50%;
                    }
                    
                    input:checked + .toggle-slider {
                        background-color: #ff4444;
                    }
                    
                    input:checked + .toggle-slider:before {
                        transform: translateX(26px);
                    }
                    
                    .toggle-label {
                        font-size: 16px;
                        color: #666;
                    }
                    
                    /* Hide sections based on mode */
                    .mode-section {
                        display: none;
                    }
                    
                    .mode-section.active {
                        display: block;
                    }

                </style>
            </head>
            <body>
                <div class="container">
                    <img src="/static/whisperlogo.png" alt="Whisper Logo" style="max-width: 700px; height: auto; margin: 20px;">
                    <h1>Whisper Transcription Service</h1>
                    
                    <div class="toggle-container">
                        <span class="toggle-label">Upload File</span>
                        <label class="toggle-switch">
                            <input type="checkbox" id="mode-toggle">
                            <span class="toggle-slider"></span>
                        </label>
                        <span class="toggle-label">Record Audio</span>
                    </div>
                    
                    <div id="record-section" class="mode-section">
                        <div class="record-container">
                            <button id="recordButton" class="record-button">Start Recording</button>
                            <div id="timer" style="margin: 10px 0;">00:00</div>
                        </div>
                        
                        <div class="transcription-container" id="transcription-container" style="display: none;">
                            <h2>Transcriptions</h2>
                            <img src="/static/spinner_red.gif" class="spinner" id="spinner">
                            <div id="transcriptions"></div>
                        </div>
                    </div>
                    
                    <div id="upload-section" class="mode-section active">
                        <form action="/transcribe" method="post" enctype="multipart/form-data" id="upload-form">
                            <div class="drop-zone" id="drop-zone">
                                <p>Drag and drop an audio file here</p>
                                <p>or</p>
                                <p>Click to select a file</p>
                                <input type="file" name="file" accept="audio/*" id="file-input" style="display: none;">
                            </div>
                            <div id="file-name"></div>
                            <button type="submit" class="submit-btn">Transcribe</button>
                        </form>
                        
                        <div class="transcription-container" id="upload-transcription-container" style="display: none;">
                            <h2>Transcriptions</h2>
                            <img src="/static/spinner_green.gif" class="spinner" id="upload-spinner">
                            <div id="upload-transcriptions"></div>
                        </div>
                    </div>
                </div>

                <script>
                    const dropZone = document.getElementById('drop-zone');
                    const fileInput = document.getElementById('file-input');
                    const fileName = document.getElementById('file-name');

                    dropZone.addEventListener('click', () => fileInput.click());

                    dropZone.addEventListener('dragover', (e) => {
                        e.preventDefault();
                        dropZone.classList.add('dragover');
                    });

                    dropZone.addEventListener('dragleave', () => {
                        dropZone.classList.remove('dragover');
                    });

                    dropZone.addEventListener('drop', (e) => {
                        e.preventDefault();
                        dropZone.classList.remove('dragover');
                        fileInput.files = e.dataTransfer.files;
                        updateFileName();
                    });

                    fileInput.addEventListener('change', updateFileName);

                    function updateFileName() {
                        if (fileInput.files.length > 0) {
                            fileName.textContent = `Selected file: ${fileInput.files[0].name}`;
                        } else {
                            fileName.textContent = '';
                        }
                    }

                    let mediaRecorder;
                    let audioChunks = [];
                    let isRecording = false;
                    let startTime;
                    let timerInterval;
                    
                    const recordButton = document.getElementById('recordButton');
                    const timer = document.getElementById('timer');
                    
                    async function startRecording() {
                        try {
                            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                            mediaRecorder = new MediaRecorder(stream);
                            audioChunks = [];
                            
                            mediaRecorder.ondataavailable = (event) => {
                                audioChunks.push(event.data);
                            };
                            
                            mediaRecorder.onstop = async () => {
                                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                                const formData = new FormData();
                                formData.append('file', audioBlob, 'recording.wav');
                                
                                try {
                                    const response = await fetch('/transcribe', {
                                        method: 'POST',
                                        body: formData
                                    });
                                    
                                    const result = await response.text();
                                    
                                    // Hide spinner
                                    document.getElementById('spinner').style.display = 'none';
                                    
                                    // Add transcription with animation
                                    const transcriptionDiv = document.createElement('div');
                                    transcriptionDiv.className = 'transcription-entry';
                                    transcriptionDiv.textContent = result;
                                    document.getElementById('transcriptions').prepend(transcriptionDiv);
                                    
                                    // Trigger animation
                                    setTimeout(() => {
                                        transcriptionDiv.classList.add('show');
                                    }, 10);
                                    
                                } catch (error) {
                                    console.error('Error:', error);
                                    // Hide spinner on error too
                                    document.getElementById('spinner').style.display = 'none';
                                }
                            };
                            
                            mediaRecorder.start(1000);
                            startTime = Date.now();
                            updateTimer();
                            timerInterval = setInterval(updateTimer, 1000);
                            
                            recordButton.textContent = 'Stop Recording';
                            recordButton.classList.add('recording');
                            isRecording = true;
                            
                        } catch (error) {
                            console.error('Error accessing microphone:', error);
                            alert('Error accessing microphone. Please ensure you have granted microphone permissions.');
                        }
                    }
                    
                    function stopRecording() {
                        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                            mediaRecorder.stop();
                            mediaRecorder.stream.getTracks().forEach(track => track.stop());
                            clearInterval(timerInterval);
                            recordButton.textContent = 'Start Recording';
                            recordButton.classList.remove('recording');
                            isRecording = false;
                            timer.textContent = '00:00';
                            
                            // Show transcription container and spinner
                            document.getElementById('transcription-container').style.display = 'block';
                            document.getElementById('spinner').style.display = 'block';
                        }
                    }
                    
                    function updateTimer() {
                        const elapsed = Math.floor((Date.now() - startTime) / 1000);
                        const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
                        const seconds = (elapsed % 60).toString().padStart(2, '0');
                        timer.textContent = `${minutes}:${seconds}`;
                    }
                    
                    recordButton.addEventListener('click', () => {
                        if (!isRecording) {
                            startRecording();
                        } else {
                            stopRecording();
                        }
                    });
                    
                    // Add keyboard shortcut handler
                    document.addEventListener('keydown', (event) => {
                        // Check for Shift + R (case insensitive)
                        if (event.shiftKey && (event.key === 'R' || event.key === 'r')) {
                            event.preventDefault(); // Prevent default browser behavior
                            
                            // Toggle recording
                            if (!isRecording) {
                                startRecording();
                            } else {
                                stopRecording();
                            }
                            
                            // Visual feedback on the button
                            recordButton.classList.add('active');
                            setTimeout(() => {
                                recordButton.classList.remove('active');
                            }, 200);
                        }
                    });
                    
                    // Add toggle functionality
                    const modeToggle = document.getElementById('mode-toggle');
                    const recordSection = document.getElementById('record-section');
                    const uploadSection = document.getElementById('upload-section');
                    
                    modeToggle.addEventListener('change', () => {
                        if (modeToggle.checked) {
                            recordSection.classList.add('active');
                            uploadSection.classList.remove('active');
                        } else {
                            uploadSection.classList.add('active');
                            recordSection.classList.remove('active');
                        }
                    });
                    
                    // Handle file upload form submission
                    document.getElementById('upload-form').addEventListener('submit', async (e) => {
                        e.preventDefault();
                        
                        if (!fileInput.files.length) {
                            alert('Please select a file first');
                            return;
                        }
                        
                        // Show transcription container and spinner
                        document.getElementById('upload-transcription-container').style.display = 'block';
                        document.getElementById('upload-spinner').style.display = 'block';
                        
                        const formData = new FormData(e.target);
                        
                        try {
                            const response = await fetch('/transcribe', {
                                method: 'POST',
                                body: formData
                            });
                            
                            const result = await response.text();
                            
                            // Hide spinner
                            document.getElementById('upload-spinner').style.display = 'none';
                            
                            // Add transcription with animation
                            const transcriptionDiv = document.createElement('div');
                            transcriptionDiv.className = 'transcription-entry';
                            transcriptionDiv.textContent = result;
                            document.getElementById('upload-transcriptions').prepend(transcriptionDiv);
                            
                            // Trigger animation
                            setTimeout(() => {
                                transcriptionDiv.classList.add('show');
                            }, 10);
                            
                            // Reset file input
                            fileInput.value = '';
                            fileName.textContent = '';
                            
                        } catch (error) {
                            console.error('Error:', error);
                            // Hide spinner on error
                            document.getElementById('upload-spinner').style.display = 'none';
                            alert('Error processing file. Please try again.');
                        }
                    });
                    
                </script>
            </body>
        </html>
    '''

@app.post("/transcribe", response_class=HTMLResponse)
async def transcribe(file: UploadFile = File(...)):
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = temp_file.name

    try:
        # Transcribe the audio
        model = whisper.load_model("base")
        result = model.transcribe(temp_path)
        
        # Always return just the transcription text
        return f'{result["text"]}'
    finally:
        # Clean up the temporary file
        os.unlink(temp_path)
