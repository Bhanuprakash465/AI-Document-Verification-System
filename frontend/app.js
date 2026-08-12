/* =========================================================
   VERIFYAI FRONTEND
   ========================================================= */

const input = document.querySelector("#file-input");
const form = document.querySelector("#upload-form");
const browseButton = document.querySelector("#browse-button");
const verifyButton = document.querySelector("#verify-button");
const fileName = document.querySelector("#file-name");
const result = document.querySelector("#result");
const loader = document.querySelector("#page-loader");


// ---------------------------------------------------------
// API
// ---------------------------------------------------------

const API_BASE = window.location.pathname.startsWith("/app")
  ? ""
  : "http://127.0.0.1:8000";


// ---------------------------------------------------------
// Page loader
// ---------------------------------------------------------

window.addEventListener("load", () => {

  setTimeout(() => {
    loader.classList.add("loaded");
  }, 700);

});


// ---------------------------------------------------------
// File handling
// ---------------------------------------------------------

function setFile(file) {

  if (!file) return;


  // Size validation
  if (file.size > 10 * 1024 * 1024) {

    showError(
      "The selected file exceeds the 10 MB upload limit."
    );

    return;
  }


  // Type validation
  const allowedTypes = [
    "image/jpeg",
    "image/png",
    "application/pdf"
  ];

  if (!allowedTypes.includes(file.type)) {

    showError(
      "Please upload a JPG, PNG or PDF document."
    );

    return;
  }


  // Put file into input
  input.files = createFileList(file);


  // Update UI
  fileName.textContent =
    file.name.toUpperCase();

  verifyButton.disabled = false;

  result.classList.add("hidden");

  result.innerHTML = "";
}


function createFileList(file) {

  const dataTransfer = new DataTransfer();

  dataTransfer.items.add(file);

  return dataTransfer.files;
}


// ---------------------------------------------------------
// Browse button
// ---------------------------------------------------------

browseButton.addEventListener(
  "click",
  () => input.click()
);


// ---------------------------------------------------------
// Input change
// ---------------------------------------------------------

input.addEventListener(
  "change",
  () => {

    const file = input.files[0];

    setFile(file);

  }
);


// ---------------------------------------------------------
// Drag and drop
// ---------------------------------------------------------

[
  "dragenter",
  "dragover"
].forEach(eventName => {

  form.addEventListener(
    eventName,
    event => {

      event.preventDefault();

      form.classList.add("dragging");

    }
  );

});


[
  "dragleave",
  "drop"
].forEach(eventName => {

  form.addEventListener(
    eventName,
    event => {

      event.preventDefault();

      form.classList.remove("dragging");

    }
  );

});


form.addEventListener(
  "drop",
  event => {

    const file =
      event.dataTransfer.files[0];

    setFile(file);

  }
);


// ---------------------------------------------------------
// Verify button
// ---------------------------------------------------------

verifyButton.addEventListener(
  "click",
  verifyDocument
);


// ---------------------------------------------------------
// Verification
// ---------------------------------------------------------

async function verifyDocument() {

  const file = input.files[0];

  if (!file) return;


  // Disable UI
  verifyButton.disabled = true;

  verifyButton.innerHTML = `
    <span class="verify-label">
      ANALYSING DOCUMENT...
    </span>

    <span class="verify-arrow">
      ↗
    </span>
  `;


  // Scroll result into view area
  result.classList.add("hidden");


  const formData = new FormData();

  formData.append(
    "file",
    file
  );


  try {

    const response = await fetch(
      `${API_BASE}/verify-document`,
      {
        method: "POST",
        body: formData
      }
    );


    let data;

    try {

      data = await response.json();

    } catch {

      throw new Error(
        "The verification server returned an invalid response."
      );

    }


    if (!response.ok) {

      throw new Error(
        data.detail ||
        "Verification could not be completed."
      );

    }


    showResult(data);


  } catch (error) {

    console.error(error);


    const message =
      error instanceof TypeError
        ? "Unable to connect to the verification server. Please make sure FastAPI is running."
        : error.message;


    showError(message);


  } finally {

    verifyButton.disabled = false;

    verifyButton.innerHTML = `
      <span class="verify-label">
        VERIFY DOCUMENT
      </span>

      <span class="verify-arrow">
        →
      </span>
    `;

  }

}


// ---------------------------------------------------------
// Result rendering
// ---------------------------------------------------------

function showResult(data) {

  const fields =
    data.fields || {};

  const validation =
    data.validation || {};

  const valid =
    Boolean(validation.valid);


  const rows = [

    [
      "DOCUMENT TYPE",
      fields.document_type
    ],

    [
      "FULL NAME",
      fields.name
    ],

    [
      "AADHAAR NUMBER",
      fields.aadhaar_number
    ],

    [
      "DATE OF BIRTH",
      fields.dob
    ],

    [
      "GENDER",
      fields.gender
    ],

    [
      "PIN CODE",
      fields.pin_code
    ]

  ];


  const fieldsHTML = rows
    .map(
      ([label, value]) => {

        return `
          <div class="result-field">

            <label>
              ${escapeHtml(label)}
            </label>

            <strong>
              ${escapeHtml(
                value || "NOT DETECTED"
              )}
            </strong>

          </div>
        `;

      }
    )
    .join("");


  const errors =
    Array.isArray(validation.errors)
      ? validation.errors
      : [];


  const errorHTML =
    errors.length
      ? `
        <div class="result-errors">

          <strong>
            VALIDATION NOTES
          </strong>

          <br />

          ${errors
            .map(error =>
              escapeHtml(error)
            )
            .join("<br />")}

        </div>
      `
      : "";


  result.innerHTML = `

    <div class="result-header">

      <div>

        <span class="section-number">
          05 / RESULT
        </span>

        <h2>
          Verification
          <span class="serif">
            complete.
          </span>
        </h2>

      </div>


      <span
        class="result-status ${
          valid
            ? "valid"
            : "invalid"
        }"
      >
        ${
          valid
            ? "VALIDATED"
            : "NEEDS REVIEW"
        }
      </span>

    </div>


    <div class="result-grid">

      ${fieldsHTML}

    </div>


    ${errorHTML}

  `;


  result.classList.remove("hidden");


  // Smooth scroll
  setTimeout(() => {

    result.scrollIntoView({
      behavior: "smooth",
      block: "start"
    });

  }, 100);

}


// ---------------------------------------------------------
// Error
// ---------------------------------------------------------

function showError(message) {

  result.innerHTML = `

    <div class="error-result">

      <strong>
        VERIFICATION ERROR
      </strong>

      <br /><br />

      ${escapeHtml(message)}

    </div>

  `;


  result.classList.remove("hidden");


  result.scrollIntoView({
    behavior: "smooth",
    block: "start"
  });

}


// ---------------------------------------------------------
// HTML escaping
// ---------------------------------------------------------

function escapeHtml(value) {

  return String(value)
    .replace(
      /[&<>'"]/g,
      character => {

        const entities = {

          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          "'": "&#39;",
          '"': "&quot;"

        };

        return entities[character];

      }
    );

}


// ---------------------------------------------------------
// Keyboard accessibility
// ---------------------------------------------------------

document.addEventListener(
  "keydown",
  event => {

    if (
      event.key === "Enter" &&
      document.activeElement === verifyButton &&
      !verifyButton.disabled
    ) {

      verifyDocument();

    }

  }
);