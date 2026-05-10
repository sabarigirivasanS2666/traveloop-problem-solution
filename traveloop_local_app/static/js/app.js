function toggleNav() {
    const nav = document.getElementById('navLinks');
    if (nav) nav.classList.toggle('open');
}

function validateSignup() {
    const password = document.getElementById('password');
    const confirm = document.getElementById('confirm_password');
    const error = document.getElementById('signupError');
    if (!password || !confirm) return true;
    if (password.value !== confirm.value) {
        error.textContent = 'Passwords do not match.';
        return false;
    }
    error.textContent = '';
    return true;
}

function filterCities() {
    const query = (document.getElementById('citySearch')?.value || '').toLowerCase();
    const country = document.getElementById('countryFilter')?.value || '';
    document.querySelectorAll('.city-tile').forEach(tile => {
        const haystack = (tile.dataset.search || '').toLowerCase();
        const tileCountry = tile.dataset.country || '';
        const matchesText = haystack.includes(query);
        const matchesCountry = !country || tileCountry === country;
        tile.style.display = matchesText && matchesCountry ? '' : 'none';
    });
}

function filterActivities() {
    const query = (document.getElementById('activitySearch')?.value || '').toLowerCase();
    const costFilter = document.getElementById('activityCostFilter')?.value || 'all';
    document.querySelectorAll('.activity-template').forEach(card => {
        const haystack = (card.dataset.search || '').toLowerCase();
        const cost = Number(card.dataset.cost || 0);
        let costOk = true;
        if (costFilter === 'free') costOk = cost === 0;
        if (costFilter === 'low') costOk = cost > 0 && cost < 1000;
        if (costFilter === 'high') costOk = cost >= 1000;
        card.style.display = haystack.includes(query) && costOk ? '' : 'none';
    });
}

function setItineraryView(view) {
    const list = document.getElementById('itineraryList');
    const calendar = document.getElementById('itineraryCalendar');
    if (!list || !calendar) return;
    if (view === 'calendar') {
        list.classList.add('hidden');
        calendar.classList.remove('hidden');
    } else {
        calendar.classList.add('hidden');
        list.classList.remove('hidden');
    }
}

function copyPublicUrl() {
    const input = document.getElementById('publicUrl');
    if (!input) return;
    input.select();
    input.setSelectionRange(0, 99999);
    navigator.clipboard?.writeText(input.value);
    alert('Public itinerary URL copied.');
}

function drawBarChart(canvas, labels, values) {
    if (!canvas || !labels || !values || labels.length === 0) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.width = canvas.offsetWidth;
    const height = canvas.height;
    const padding = 36;
    const max = Math.max(...values, 1);
    const barWidth = (width - padding * 2) / labels.length - 10;
    ctx.clearRect(0, 0, width, height);
    ctx.font = '12px sans-serif';
    ctx.fillStyle = '#64748b';
    ctx.fillText('Count', 8, 16);
    values.forEach((value, index) => {
        const x = padding + index * (barWidth + 10);
        const barHeight = ((height - padding * 2) * value) / max;
        const y = height - padding - barHeight;
        ctx.fillStyle = '#2563eb';
        ctx.fillRect(x, y, barWidth, barHeight);
        ctx.fillStyle = '#102033';
        ctx.fillText(String(value), x + 4, y - 6);
        ctx.save();
        ctx.translate(x + barWidth / 2, height - 8);
        ctx.rotate(-0.55);
        ctx.fillText(String(labels[index]).slice(0, 14), 0, 0);
        ctx.restore();
    });
}

function drawBudgetChart() {
    const canvas = document.getElementById('budgetChart');
    if (!canvas) return;
    const budget = JSON.parse(canvas.dataset.budget || '{}');
    const labels = ['Transport', 'Stay', 'Meals', 'Activities'];
    const values = [budget.transport || 0, budget.stay || 0, budget.meals || 0, budget.activities || 0];
    drawBarChart(canvas, labels, values);
}

function drawAdminCharts() {
    const cityChart = document.getElementById('cityChart');
    const activityChart = document.getElementById('activityChart');
    if (cityChart) drawBarChart(cityChart, JSON.parse(cityChart.dataset.labels || '[]'), JSON.parse(cityChart.dataset.values || '[]'));
    if (activityChart) drawBarChart(activityChart, JSON.parse(activityChart.dataset.labels || '[]'), JSON.parse(activityChart.dataset.values || '[]'));
}

window.addEventListener('resize', () => {
    drawBudgetChart();
    drawAdminCharts();
});
