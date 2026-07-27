const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const captureBtn = document.getElementById('captureBtn');
const saveBtn = document.getElementById('saveBtn');
const statusMsg = document.getElementById('statusMsg');
const nameInput = document.getElementById('nameInput');
const studentIdInput = document.getElementById('studentIdInput');

let capturedBlob = null;

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function setStatus(message, type = '') {
    statusMsg.textContent = message;
    statusMsg.className = `status ${type}`.trim();
}

const csrftoken = getCookie('csrftoken');

navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } })
    .then(stream => {
        video.srcObject = stream;
        setStatus('Camera ready.');
    })
    .catch(err => {
        setStatus('Camera access denied or unavailable.', 'error');
        AppUI.toast('Camera access denied or unavailable.', 'error');
        console.error(err);
    });

captureBtn.addEventListener('click', async () => {
    const approved = await AppUI.confirmAction({
        title: 'Capture student photo?',
        message: 'Make sure the student is facing the camera clearly.',
        confirmText: 'Capture'
    });

    if (!approved) return;

    const context = canvas.getContext('2d');
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(blob => {
        capturedBlob = blob;
        setStatus('Photo captured. Review the details and save.', 'success');
        AppUI.toast('Photo captured successfully.', 'success');
        saveBtn.disabled = false;
    }, 'image/jpeg', 0.9);
});

saveBtn.addEventListener('click', async () => {
    const studentId = studentIdInput.value.trim();
    const name = nameInput.value.trim();

    if (!studentId || !name) {
        setStatus('Please enter both student ID and name.', 'error');
        AppUI.toast('Student ID and name are required.', 'error');
        return;
    }

    if (!capturedBlob) {
        setStatus('Please capture a photo first.', 'error');
        AppUI.toast('Capture a photo before saving.', 'error');
        return;
    }

    const approved = await AppUI.confirmAction({
        title: 'Save student registration?',
        message: `Register ${name} with student ID ${studentId}.`,
        confirmText: 'Save'
    });

    if (!approved) return;

    const formData = new FormData();
    formData.append('student_id', studentId);
    formData.append('name', name);
    formData.append('photo', capturedBlob, `${studentId}.jpg`);

    saveBtn.disabled = true;
    setStatus('Registering...');
    AppUI.toast('Saving student registration...');

    fetch('/api/students/register/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken
        },
        body: formData
    })
    .then(res => res.json().then(data => ({ status: res.status, data })))
    .then(({ status, data }) => {
        if (status === 201) {
            setStatus(`${data.name} registered successfully.`, 'success');
            AppUI.toast(`${data.name} registered successfully.`, 'success');
            studentIdInput.value = '';
            nameInput.value = '';
            capturedBlob = null;
        } else {
            setStatus(data.error || 'Registration failed.', 'error');
            AppUI.toast(data.error || 'Registration failed.', 'error');
            saveBtn.disabled = false;
        }
    })
    .catch(err => {
        setStatus('Something went wrong.', 'error');
        AppUI.toast('Something went wrong while registering.', 'error');
        saveBtn.disabled = false;
        console.error(err);
    });
});
