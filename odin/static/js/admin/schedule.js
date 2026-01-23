document.addEventListener("DOMContentLoaded", function () {
  const container = document.getElementById("periods-container");
  const addButton = document.getElementById("add-period");
  const typeButton = document.getElementById("id_type");

  let periodIndex = 0;
  updateIndices();

  addButton.addEventListener("click", function () {
    addPeriod();
  });

  typeButton.addEventListener("change", function (e) {
    const periodItems = container.querySelectorAll(".period-item");
    let selectedType = e.target.value;

    periodItems.forEach(item => {
      let targetTemp = item.querySelector("input[name$='-target_temp']");
      let targetState = item.querySelector("select[name$='-target_state']");

      if (selectedType === "SERVO") {
        targetTemp.required = true;
        targetTemp.closest(".field-group").classList.remove("hidden");

        targetState.required = false;
        targetState.closest(".field-group").classList.add("hidden");
      }

      else if (selectedType === "PUMP") {
        targetTemp.required = false;
        targetTemp.closest(".field-group").classList.add("hidden");

        targetState.required = true;
        targetState.closest(".field-group").classList.remove("hidden");
      }

      else {
        targetTemp.required = false;
        targetTemp.closest(".field-group").classList.add("hidden");

        targetState.required = false;
        targetState.closest(".field-group").classList.add("hidden");
      }
    });
  });

  container.addEventListener("click", function (e) {
    if (e.target.classList.contains("remove-period")) {
      e.target.closest(".period-item").remove();
      updateIndices();
    }
  });

  function addPeriod() {
    const periodHtml = createPeriodHtml(periodIndex);
    container.insertAdjacentHTML("beforeend", periodHtml);
    periodIndex++;
  }

  function createPeriodHtml(index) {
    return `
      <div class="period-item" data-index="${index}">
        <div class="period-fields">
          <div class="field-group">
            <label class="required">Время начала</label>
            <input type="time" name="schedule-periods-${index}-start_time" required>
          </div>
          <div class="field-group">
            <label class="required">Время окончания</label>
            <input type="time" name="schedule-periods-${index}-end_time" required>
          </div>
          <div class="field-group${window.relayType === 'SERVO' ? '' : ' hidden'}">
            <label>Температура &deg;C</label>
            <input type="number" step="0.1" name="schedule-periods-${index}-target_temp" required>
          </div>
          <div class="field-group${window.relayType === 'PUMP' ? '' : ' hidden'}">
            <label>Target State</label>
            <select name="schedule-periods-${index}-target_state" required>
              <option value="ON">ON</option>
              <option value="OFF">OFF</option>
            </select>
          </div>
          <div class="field-group actions">
            <button type="button" class="remove-period btn btn-danger">Удалить</button>
          </div>
        </div>
      </div>
    `;
  }

  function updateIndices() {
    const periods = container.querySelectorAll(".period-item");
    periods.forEach((period, index) => {
      period.setAttribute("data-index", index);

      const inputs = period.querySelectorAll("input, select");

      inputs.forEach((input) => {
        if (input.name) {
          input.name = input.name.replace(
            /schedule-periods-\d+-/,
            `schedule-periods-${index}-`,
          );
        }
      });
    });
    periodIndex = periods.length;
  }
});
