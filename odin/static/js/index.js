document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("target-temp-modal");
  const form = document.getElementById("target-temp-form");
  const tempInput = document.getElementById("target-temp-input");
  const sensorInput = document.getElementById("target-temp-sensor-id");
  const messageEl = document.getElementById("target-temp-message");
  const closeBtn = modal ? modal.querySelector(".modal__close") : null;

  if (!modal || !form || !tempInput || !sensorInput) {
    return;
  }

  const setMessage = (text, isError = false) => {
    if (!messageEl) {
      return;
    }
    messageEl.textContent = text || "";
    messageEl.style.color = isError ? "#c92a2a" : "#87C540";
  };

  const openModal = (sensorEl) => {
    if (!sensorEl) {
      return;
    }
    const sensorId = sensorEl.dataset.sensorId;
    const targetTemp = sensorEl.dataset.targetTemp || "";
    sensorInput.value = sensorId || "";
    tempInput.value = targetTemp;
    setMessage("");
    modal.classList.add("is-open");
    tempInput.focus();
  };

  const closeModal = () => {
    modal.classList.remove("is-open");
    setMessage("");
    form.reset();
  };

  document.querySelectorAll('a[href="#edit"]').forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      const sensorEl = link.closest(".sensor");
      openModal(sensorEl);
    });
  });

  closeBtn?.addEventListener("click", closeModal);
  modal.addEventListener("click", (event) => {
    if (event.target === modal) {
      closeModal();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && modal.classList.contains("is-open")) {
      closeModal();
    }
  });

  const getCsrfToken = () => {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : null;
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const sensorId = sensorInput.value;
    const targetTemp = tempInput.value;

    if (!sensorId || !targetTemp) {
      setMessage("Target temperature is required.", true);
      return;
    }

    setMessage("Saving...");
    try {
      const response = await fetch(`/api/v1/sensors/${sensorId}/`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken() || "",
        },
        credentials: "same-origin",
        body: JSON.stringify({ context: { target_temp: targetTemp } }),
      });

      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }

      setMessage("Saved.");
      setTimeout(closeModal, 700);
    } catch (error) {
      setMessage("Could not save target temperature.", true);
      console.error(error);
    }
  });
});
