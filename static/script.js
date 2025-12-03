document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('planner-form');
    const obstaclesList = document.getElementById('obstacles-list');
    const addObstacleBtn = document.getElementById('add-obstacle-btn');
    const canvas = document.getElementById('wall-canvas');
    const ctx = canvas.getContext('2d');

    // Playback elements
    const playbackControls = document.querySelector('.playback-controls');
    const playBtn = document.getElementById('play-btn');
    const pauseBtn = document.getElementById('pause-btn');
    const resetBtn = document.getElementById('reset-btn');
    const slider = document.getElementById('playback-slider');
    const statusDisplay = document.getElementById('playback-status');
    const metadataDisplay = document.getElementById('metadata-display');

    // State
    let currentTrajectory = null;
    let animationId = null;
    let currentFrame = 0;
    let isPlaying = false;
    let scale = 1;
    let offsetX = 0;
    let offsetY = 0;

    // Add initial obstacle example
    addObstacle();

    // Event Listeners
    addObstacleBtn.addEventListener('click', addObstacle);
    form.addEventListener('submit', handleFormSubmit);

    playBtn.addEventListener('click', play);
    pauseBtn.addEventListener('click', pause);
    resetBtn.addEventListener('click', reset);
    slider.addEventListener('input', (e) => {
        currentFrame = parseInt(e.target.value);
        draw();
        updateStatus();
    });

    function addObstacle() {
        const div = document.createElement('div');
        div.className = 'obstacle-item';
        div.innerHTML = `
            <button type="button" class="remove-obstacle">×</button>
            <label>X: <input type="number" class="obs-x" value="1" step="0.1" required></label>
            <label>Y: <input type="number" class="obs-y" value="1" step="0.1" required></label>
            <label>W: <input type="number" class="obs-w" value="0.5" step="0.1" required></label>
            <label>H: <input type="number" class="obs-h" value="0.5" step="0.1" required></label>
        `;

        div.querySelector('.remove-obstacle').addEventListener('click', () => {
            div.remove();
        });

        obstaclesList.appendChild(div);
    }

    async function handleFormSubmit(e) {
        e.preventDefault();

        const wallWidth = parseFloat(document.getElementById('wall-width').value);
        const wallHeight = parseFloat(document.getElementById('wall-height').value);

        const obstacles = Array.from(document.querySelectorAll('.obstacle-item')).map(item => ({
            x: parseFloat(item.querySelector('.obs-x').value),
            y: parseFloat(item.querySelector('.obs-y').value),
            width: parseFloat(item.querySelector('.obs-w').value),
            height: parseFloat(item.querySelector('.obs-h').value)
        }));

        const payload = {
            job_name: "Web Job " + new Date().toISOString(),
            wall: { width: wallWidth, height: wallHeight },
            obstacles: obstacles,
            planner_params: {
                tool_width: parseFloat(document.getElementById('tool-width').value),
                overlap: parseFloat(document.getElementById('overlap').value),
                safe_margin: parseFloat(document.getElementById('safe-margin').value),
                orientation: "auto"
            }
        };

        try {
            const response = await fetch('/api/trajectories/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const err = await response.json();
                alert('Error: ' + JSON.stringify(err.detail));
                return;
            }

            currentTrajectory = await response.json();
            setupVisualization();

        } catch (err) {
            console.error(err);
            alert('Failed to generate trajectory');
        }
    }

    function setupVisualization() {
        if (!currentTrajectory) return;

        // Show controls
        playbackControls.style.display = 'block';
        metadataDisplay.style.display = 'block';

        // Update metadata
        document.getElementById('meta-length').textContent = currentTrajectory.meta.path_length_m.toFixed(2);
        document.getElementById('meta-coverage').textContent = (currentTrajectory.meta.coverage_fraction * 100).toFixed(1);
        document.getElementById('meta-waypoints').textContent = currentTrajectory.meta.num_waypoints;

        // Setup slider
        slider.max = currentTrajectory.waypoints.length - 1;
        slider.value = 0;
        currentFrame = 0;

        // Calculate scale to fit canvas
        const wall = currentTrajectory.wall;
        const padding = 40;
        const availW = canvas.parentElement.clientWidth - padding * 2;
        const availH = 600 - padding * 2;

        canvas.width = canvas.parentElement.clientWidth;
        canvas.height = 600;

        const scaleX = availW / wall.width;
        const scaleY = availH / wall.height;
        scale = Math.min(scaleX, scaleY);

        // Center the wall
        offsetX = (canvas.width - wall.width * scale) / 2;
        offsetY = (canvas.height - wall.height * scale) / 2;

        // Initial draw
        draw();
        updateStatus();
    }

    function draw() {
        if (!currentTrajectory) return;

        // Clear
        ctx.fillStyle = '#252525';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Transform coordinate system (flip Y for standard cartesian)
        ctx.save();
        ctx.translate(offsetX, canvas.height - offsetY);
        ctx.scale(scale, -scale);

        // Draw Wall
        ctx.strokeStyle = '#555';
        ctx.lineWidth = 2 / scale;
        ctx.strokeRect(0, 0, currentTrajectory.wall.width, currentTrajectory.wall.height);

        // Draw Obstacles (Original)
        ctx.fillStyle = 'rgba(255, 85, 85, 0.5)';
        currentTrajectory.obstacles.forEach(obs => {
            ctx.fillRect(obs.x, obs.y, obs.width, obs.height);
        });

        // Draw Forbidden Rects (Inflated)
        ctx.strokeStyle = 'rgba(255, 85, 85, 0.8)';
        ctx.lineWidth = 1 / scale;
        ctx.setLineDash([5, 5]);
        currentTrajectory.forbidden_rects.forEach(rect => {
            ctx.strokeRect(rect.x, rect.y, rect.width, rect.height);
        });
        ctx.setLineDash([]);

        // Draw Path
        if (currentTrajectory.waypoints.length > 0) {
            ctx.beginPath();
            ctx.strokeStyle = '#bb86fc';
            ctx.lineWidth = 2 / scale;

            const points = currentTrajectory.waypoints;
            ctx.moveTo(points[0].x, points[0].y);

            // Draw up to current frame
            for (let i = 1; i <= currentFrame; i++) {
                ctx.lineTo(points[i].x, points[i].y);
            }
            ctx.stroke();

            // Draw Robot at current position
            const currentPos = points[currentFrame];
            ctx.fillStyle = '#03dac6';
            const toolW = currentTrajectory.planner_params.tool_width;

            ctx.save();
            ctx.translate(currentPos.x, currentPos.y);
            ctx.rotate(currentPos.theta);
            // Draw robot as a rectangle representing tool width
            ctx.fillRect(-0.1, -toolW / 2, 0.2, toolW);
            ctx.restore();
        }

        ctx.restore();
    }

    function play() {
        if (isPlaying) return;
        isPlaying = true;
        animate();
    }

    function pause() {
        isPlaying = false;
        cancelAnimationFrame(animationId);
    }

    function reset() {
        pause();
        currentFrame = 0;
        slider.value = 0;
        draw();
        updateStatus();
    }

    function animate() {
        if (!isPlaying) return;

        if (currentFrame < currentTrajectory.waypoints.length - 1) {
            currentFrame++;
            slider.value = currentFrame;
            draw();
            updateStatus();
            animationId = requestAnimationFrame(animate);
        } else {
            pause();
        }
    }

    function updateStatus() {
        if (currentTrajectory) {
            statusDisplay.textContent = `Frame: ${currentFrame} / ${currentTrajectory.waypoints.length - 1}`;
        }
    }
});
