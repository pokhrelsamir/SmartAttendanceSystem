const video = document.getElementById('video');
const overlay = document.getElementById('overlay');
const ctx = overlay.getContext('2d');
const statusMsg = document.getElementById('statusMsg');
const markBtn = document.getElementById('markBtn');
const attendanceTableBody = document.getElementById('attendanceTableBody');
const videoWrapper = document.getElementById('videoWrapper');

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

navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, frameRate: { ideal: 30, min: 15 } } })
    .then(stream => {
        video.srcObject = stream;
        setStatus('Detecting faces...');
        refreshAttendanceTable();
    })
    .catch(err => {
        setStatus('Camera access denied.', 'error');
        videoWrapper.classList.add('is-unavailable');
        markBtn.disabled = true;
        refreshAttendanceTable();
        AppUI.toast('Camera access denied.', 'error');
        console.error(err);
    });

let detectIntervalId = null;

video.addEventListener('loadedmetadata', () => {
    videoWrapper.style.aspectRatio = `${video.videoWidth} / ${video.videoHeight}`;
    overlay.width = video.videoWidth;
    overlay.height = video.videoHeight;

    if (detectIntervalId !== null) {
        clearInterval(detectIntervalId);
    }
    detectIntervalId = setInterval(captureAndDetect, 300);
});

let detectionInFlight = false;

function captureAndDetect() {
    if (detectionInFlight || !video.videoWidth || !video.videoHeight) return;
    detectionInFlight = true;

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(blob => {
        const formData = new FormData();
        formData.append('photo', blob, 'frame.jpg');

        fetch('/api/attendance/detect_live/', {
            method: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
            body: formData
        })
        .then(res => res.json())
        .then(data => drawBoxes(data.faces || []))
        .catch(err => console.error(err))
        .finally(() => { detectionInFlight = false; });
    }, 'image/jpeg', 0.85);
}

function drawBoxes(faces) {
    ctx.clearRect(0, 0, overlay.width, overlay.height);

    faces.forEach(face => {
        const [x1, y1, x2, y2] = face.bbox;
        const color = face.registered ? '#22c55e' : '#ef4444';

        ctx.strokeStyle = color;
        ctx.lineWidth = 3;
        ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

        if (face.name) {
            ctx.fillStyle = color;
            ctx.font = '18px Arial';
            ctx.fillText(face.name, x1, Math.max(y1 - 8, 20));
        }
    });
}

markBtn.addEventListener('click', async () => {
    const approved = await AppUI.confirmAction({
        title: 'Mark attendance?',
        message: 'The system will capture live frames, verify liveness and record the attendance time.',
        confirmText: 'Mark'
    });

    if (!approved) return;

    markBtn.disabled = true;
    setStatus('Capturing frames. Please look at the camera naturally.');
    AppUI.toast('Capturing attendance frames...');

    const frames = [];
    const totalFrames = 15;
    const intervalMs = 200;
    let count = 0;

    const captureInterval = setInterval(() => {
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);

        canvas.toBlob(blob => {
            frames.push(blob);
            count++;

            if (count >= totalFrames) {
                clearInterval(captureInterval);
                submitFrames(frames);
            }
        }, 'image/jpeg', 0.9);
    }, intervalMs);
});

function submitFrames(frames) {
    setStatus('Verifying liveness and attendance window...');

    const formData = new FormData();
    frames.forEach((blob, i) => {
        formData.append('photos', blob, `frame_${i}.jpg`);
    });

    fetch('/api/attendance/mark_live/', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrftoken },
        body: formData
    })
    .then(res => res.json().then(data => ({ status: res.status, data })))
    .then(({ status, data }) => {
        if (status === 200) {
            setStatus(data.message, 'success');
            AppUI.toast(data.message, 'success');
            refreshAttendanceTable();
        } else {
            const errorMessage = data.error || 'Attendance marking failed.';
            setStatus(errorMessage, 'error');
            AppUI.toast(errorMessage, 'error');
        }
        markBtn.disabled = false;
    })
    .catch(err => {
        setStatus('Something went wrong.', 'error');
        AppUI.toast('Something went wrong while marking attendance.', 'error');
        markBtn.disabled = false;
        console.error(err);
    });
}

function refreshAttendanceTable() {
    fetch('/api/attendance/')
        .then(res => res.json())
        .then(records => {
            attendanceTableBody.innerHTML = '';

            if (!Array.isArray(records) || records.length === 0) {
                attendanceTableBody.innerHTML = '<tr><td class="empty-row" colspan="5">No attendance taken in the last 24 hours.</td></tr>';
                return;
            }

            records.forEach(r => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${escapeHtml(r.student_id)}</td>
                    <td>${escapeHtml(r.student_name)}</td>
                    <td>${escapeHtml(r.teacher_name)}</td>
                    <td>${escapeHtml(r.date)}</td>
                    <td>${escapeHtml(formatTime(r.time))}</td>
                `;
                attendanceTableBody.appendChild(row);
            });
        })
        .catch(err => {
            AppUI.toast('Could not load attendance records.', 'error');
            console.error(err);
        });
}

function formatTime(timeValue) {
    return timeValue ? timeValue.split('.')[0] : '';
}

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    }[char]));
}
