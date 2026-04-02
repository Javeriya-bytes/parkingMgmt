setInterval(() => {
  if (!window.SLOT_API_URL) return;
  fetch(window.SLOT_API_URL)
    .then((r) => r.json())
    .then((data) => {
      const available = document.getElementById('available-count');
      const occupied = document.getElementById('occupied-count');
      if (available) available.textContent = data.counts.available;
      if (occupied) occupied.textContent = data.counts.occupied;

      const slotsByNumber = {};
      data.slots.forEach((slot) => {
        slotsByNumber[slot.slot_number] = slot;
      });

      document.querySelectorAll('.slot[data-slot-number]').forEach((card) => {
        const slotNumber = card.getAttribute('data-slot-number');
        const slotData = slotsByNumber[slotNumber];
        if (!slotData) return;

        card.classList.remove('slot-free', 'slot-busy');
        card.classList.add(slotData.status === 'available' ? 'slot-free' : 'slot-busy');
        const statusText = card.querySelector('.slot-status-text');
        if (statusText) {
          statusText.textContent = slotData.status === 'available' ? 'Available' : 'Occupied';
        }
      });
    })
    .catch(() => {});
}, 5000);

document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('booking-form');
  if (!form) return;
  form.addEventListener('submit', function (e) {
    const durationField = form.querySelector('input[name="duration_minutes"]');
    if (durationField && Number(durationField.value) < 30) {
      e.preventDefault();
      alert('Duration must be at least 30 minutes.');
    }
  });
});
