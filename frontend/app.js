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
    if (loader) {
      loader.classList.add("loaded");
    }
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
  try {

    input.files = createFileList(file);

  } catch (error) {

    console.error(
      "Unable to set selected file:",
      error
    );

    showError(
      "Unable to select this file. Please try again."
    );

    return;
  }


  // Update UI
  fileName.textContent =
    file.name.toUpperCase();

  verifyButton.disabled = false;

  result.classList.add("hidden");

  result.innerHTML = "";
}


function createFileList(file) {

  const dataTransfer =
    new DataTransfer();

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

  if (!file) {

    showError(
      "Please select a document first."
    );

    return;
  }


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


  // Hide previous result
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


    console.log(
      "Verification response:",
      data
    );


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


// =========================================================
// DOCUMENT FIELD CONFIGURATION
// =========================================================

const DOCUMENT_FIELDS = {

  aadhaar: [
    ["FULL NAME", "name"],
    ["AADHAAR NUMBER", "aadhaar_number"],
    ["DATE OF BIRTH", "dob"],
    ["GENDER", "gender"],
    ["ADDRESS", "address"],
    ["PIN CODE", "pin_code"]
  ],

  pan: [
    ["FULL NAME", "name"],
    ["PAN NUMBER", "pan_number"],
    ["FATHER NAME", "father_name"],
    ["DATE OF BIRTH", "dob"]
  ],

  passport: [
    ["FULL NAME", "name"],
    ["PASSPORT NUMBER", "passport_number"],
    ["NATIONALITY", "nationality"],
    ["DATE OF BIRTH", "dob"],
    ["PLACE OF BIRTH", "place_of_birth"],
    ["DATE OF ISSUE", "date_of_issue"],
    ["DATE OF EXPIRY", "date_of_expiry"]
  ],

  voter_id: [
    ["FULL NAME", "name"],
    ["VOTER ID", "voter_id"],
    ["EPIC NUMBER", "epic_number"],
    ["DATE OF BIRTH", "dob"],
    ["GENDER", "gender"],
    ["ADDRESS", "address"]
  ],

  driving_license: [
    ["FULL NAME", "name"],
    ["LICENCE NUMBER", "license_number"],
    ["DATE OF BIRTH", "dob"],
    ["DATE OF ISSUE", "date_of_issue"],
    ["DATE OF EXPIRY", "date_of_expiry"],
    ["ADDRESS", "address"]
  ]

};


// =========================================================
// DOCUMENT DISPLAY NAMES
// =========================================================

const DOCUMENT_NAMES = {

  aadhaar: "AADHAAR CARD",

  pan: "PAN CARD",

  passport: "PASSPORT",

  voter_id: "VOTER ID",

  driving_license: "DRIVING LICENCE",

  unknown: "UNKNOWN DOCUMENT"

};


// ---------------------------------------------------------
// Get document fields
// ---------------------------------------------------------

function getDocumentFields(
  documentType,
  fields
) {

  const configuredFields =
    DOCUMENT_FIELDS[documentType];


  if (configuredFields) {

    return configuredFields;

  }


  // Generic fallback
  return [

    ["FULL NAME", "name"],

    ["DATE OF BIRTH", "dob"],

    ["ADDRESS", "address"]

  ].filter(
    ([label, key]) =>
      fields[key] !== null &&
      fields[key] !== undefined
  );

}


// ---------------------------------------------------------
// Get document name
// ---------------------------------------------------------

function getDocumentName(
  documentType,
  data
) {

  if (
    data.document &&
    data.document.display_name
  ) {

    return data.document.display_name
      .toUpperCase();

  }


  return (
    DOCUMENT_NAMES[documentType] ||
    documentType
      .replace(/_/g, " ")
      .toUpperCase()
  );

}


// ---------------------------------------------------------
// Result rendering
// ---------------------------------------------------------

function showResult(data) {

  const fields =
    data.fields || {};


  const validation =
    data.validation || {};


  const documentInfo =
    data.document || {};


  const documentType =
    (
      data.document_type ||
      fields.document_type ||
      documentInfo.document_type ||
      "unknown"
    ).toLowerCase();


  const valid =
    Boolean(validation.valid);


  const displayName =
    getDocumentName(
      documentType,
      data
    );


  // =======================================================
  // Build fields dynamically
  // =======================================================

  const fieldDefinitions =
    getDocumentFields(
      documentType,
      fields
    );


  const rows = [

    [
      "DOCUMENT TYPE",
      displayName
    ],

    ...fieldDefinitions

  ];


  const fieldsHTML = rows
    .map(
      ([label, keyOrValue]) => {

        let value;


        // Document type is already a display value
        if (
          label === "DOCUMENT TYPE"
        ) {

          value = keyOrValue;

        } else {

          value =
            fields[keyOrValue];

        }


        return `
          <div class="result-field">

            <label>
              ${escapeHtml(label)}
            </label>

            <strong>
              ${escapeHtml(
                value ||
                "NOT DETECTED"
              )}
            </strong>

          </div>
        `;

      }
    )
    .join("");


  // =======================================================
  // Validation errors
  // =======================================================

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
            .map(
              error =>
                escapeHtml(error)
            )
            .join("<br />")}

        </div>
      `
      : "";


  // =======================================================
  // Confidence
  // =======================================================

  const confidence =
    documentInfo.confidence;


  const confidenceHTML =
    typeof confidence === "number"
      ? `
        <div class="result-confidence">

          <span>
            DETECTION CONFIDENCE
          </span>

          <strong>
            ${Math.round(
              confidence * 100
            )}%
          </strong>

        </div>
      `
      : "";


  // =======================================================
  // Status
  // =======================================================

  const statusText =
    valid
      ? "VALIDATED"
      : (
          validation.status === "unsupported"
            ? "UNSUPPORTED"
            : "NEEDS REVIEW"
        );


  // =======================================================
  // Result HTML
  // =======================================================

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
        ${statusText}
      </span>

    </div>


    <div class="result-document-type">

      <span>
        DETECTED DOCUMENT
      </span>

      <strong>
        ${escapeHtml(
          displayName
        )}
      </strong>

    </div>


    <div class="result-grid">

      ${fieldsHTML}

    </div>


    ${confidenceHTML}


    ${errorHTML}


  `;


  result.classList.remove(
    "hidden"
  );


  // =======================================================
  // Smooth scroll
  // =======================================================

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

      <br />
      <br />

      ${escapeHtml(message)}

    </div>

  `;


  result.classList.remove(
    "hidden"
  );


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


        return entities[
          character
        ];

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
      document.activeElement ===
        verifyButton &&
      !verifyButton.disabled
    ) {

      verifyDocument();

    }

  }
);