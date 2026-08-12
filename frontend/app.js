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


// =========================================================
// API
// =========================================================

const API_BASE = window.location.pathname.startsWith("/app")
    ? ""
    : "http://127.0.0.1:8000";


// =========================================================
// PAGE LOADER
// =========================================================

window.addEventListener("load", () => {

    setTimeout(() => {

        if (loader) {
            loader.classList.add("loaded");
        }

    }, 700);

});


// =========================================================
// FILE HANDLING
// =========================================================

function setFile(file) {

    if (!file) {
        return;
    }

    // -----------------------------------------------------
    // FILE SIZE
    // -----------------------------------------------------

    if (file.size > 10 * 1024 * 1024) {

        showError(
            "The selected file exceeds the 10 MB upload limit."
        );

        return;
    }


    // -----------------------------------------------------
    // FILE TYPE
    // -----------------------------------------------------

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


    // -----------------------------------------------------
    // SET INPUT
    // -----------------------------------------------------

    input.files = createFileList(file);


    // -----------------------------------------------------
    // UPDATE UI
    // -----------------------------------------------------

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


// =========================================================
// BROWSE BUTTON
// =========================================================

browseButton.addEventListener(
    "click",
    () => input.click()
);


// =========================================================
// INPUT CHANGE
// =========================================================

input.addEventListener(
    "change",
    () => {

        const file = input.files[0];

        setFile(file);

    }
);


// =========================================================
// DRAG & DROP
// =========================================================

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


// =========================================================
// VERIFY BUTTON
// =========================================================

verifyButton.addEventListener(
    "click",
    verifyDocument
);


// =========================================================
// VERIFY DOCUMENT
// =========================================================

async function verifyDocument() {

    const file = input.files[0];

    if (!file) {
        return;
    }


    // -----------------------------------------------------
    // DISABLE UI
    // -----------------------------------------------------

    verifyButton.disabled = true;

    verifyButton.innerHTML = `
        <span class="verify-label">
            ANALYSING DOCUMENT...
        </span>

        <span class="verify-arrow">
            ↗
        </span>
    `;


    result.classList.add("hidden");


    // -----------------------------------------------------
    // FORM DATA
    // -----------------------------------------------------

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


        // -------------------------------------------------
        // RESPONSE
        // -------------------------------------------------

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


// =========================================================
// RESULT FIELD HELPER
// =========================================================

function createField(
    label,
    value
) {

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


// =========================================================
// RESULT FIELDS BY DOCUMENT TYPE
// =========================================================

function getDocumentFields(
    documentType,
    fields
) {

    // =====================================================
    // AADHAAR
    // =====================================================

    if (documentType === "aadhaar") {

        return [

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
            ],

            [
                "ADDRESS",
                fields.address
            ]

        ];
    }


    // =====================================================
    // PAN
    // =====================================================

    if (documentType === "pan") {

        return [

            [
                "FULL NAME",
                fields.name
            ],

            [
                "PAN NUMBER",
                fields.pan_number
            ],

            [
                "FATHER NAME",
                fields.father_name
            ],

            [
                "DATE OF BIRTH",
                fields.dob
            ]

        ];
    }


    // =====================================================
    // PASSPORT
    // =====================================================

    if (documentType === "passport") {

        return [

            [
                "FULL NAME",
                fields.name
            ],

            [
                "PASSPORT NUMBER",
                fields.passport_number
            ],

            [
                "NATIONALITY",
                fields.nationality
            ],

            [
                "DATE OF BIRTH",
                fields.date_of_birth
            ],

            [
                "SEX",
                fields.sex
            ],

            [
                "DATE OF ISSUE",
                fields.date_of_issue
            ],

            [
                "DATE OF EXPIRY",
                fields.date_of_expiry
            ],

            [
                "PLACE OF BIRTH",
                fields.place_of_birth
            ],

            [
                "PLACE OF ISSUE",
                fields.place_of_issue
            ]

        ];
    }


    // =====================================================
    // DRIVING LICENCE
    // =====================================================

    if (documentType === "driving_license") {

        return [

            [
                "FULL NAME",
                fields.name
            ],

            [
                "LICENCE NUMBER",
                fields.licence_number ||
                fields.license_number
            ],

            [
                "DATE OF BIRTH",
                fields.date_of_birth
            ],

            [
                "ISSUE DATE",
                fields.issue_date
            ],

            [
                "EXPIRY DATE",
                fields.expiry_date
            ],

            [
                "BLOOD GROUP",
                fields.blood_group
            ],

            [
                "VEHICLE CLASSES",
                Array.isArray(
                    fields.vehicle_classes
                )
                    ? fields.vehicle_classes.join(", ")
                    : fields.vehicle_classes
            ],

            [
                "ADDRESS",
                fields.address
            ]

        ];
    }


    // =====================================================
    // VOTER ID
    // =====================================================

    if (documentType === "voter_id") {

        return [

            [
                "FULL NAME",
                fields.name
            ],

            [
                "VOTER ID",
                fields.voter_id ||
                fields.epic_number
            ],

            [
                "DATE OF BIRTH",
                fields.dob ||
                fields.date_of_birth
            ],

            [
                "GENDER",
                fields.gender
            ],

            [
                "ADDRESS",
                fields.address
            ]

        ];
    }


    // =====================================================
    // FALLBACK
    // =====================================================

    return [

        [
            "DOCUMENT TYPE",
            fields.document_type
        ],

        [
            "FULL NAME",
            fields.name
        ]

    ];
}


// =========================================================
// SHOW RESULT
// =========================================================

function showResult(data) {

    const fields =
        data.fields || {};

    const validation =
        data.validation || {};

    const document =
        data.document || {};


    const documentType =
        data.document_type ||
        fields.document_type ||
        "unknown";


    const displayName =
        document.display_name ||
        formatDocumentType(
            documentType
        );


    const valid =
        Boolean(validation.valid);


    // -----------------------------------------------------
    // GET DOCUMENT-SPECIFIC FIELDS
    // -----------------------------------------------------

    const rows =
        getDocumentFields(
            documentType,
            fields
        );


    // -----------------------------------------------------
    // CREATE HTML
    // -----------------------------------------------------

    const fieldsHTML = rows
        .map(
            ([label, value]) =>
                createField(
                    label,
                    value
                )
        )
        .join("");


    // -----------------------------------------------------
    // VALIDATION ERRORS
    // -----------------------------------------------------

    const errors =
        Array.isArray(
            validation.errors
        )
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


    // -----------------------------------------------------
    // CONFIDENCE
    // -----------------------------------------------------

    const confidence =
        document.confidence != null
            ? Math.round(
                Number(
                    document.confidence
                ) * 100
            )
            : null;


    const confidenceHTML =
        confidence !== null
            ? `
                <div class="result-confidence">

                    DETECTION CONFIDENCE

                    <strong>
                        ${confidence}%
                    </strong>

                </div>
            `
            : "";


    // -----------------------------------------------------
    // RESULT
    // -----------------------------------------------------

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


        <div class="detected-document">

            DETECTED DOCUMENT

            <strong>
                ${escapeHtml(
                    displayName
                )}
            </strong>

        </div>


        <div class="result-grid">

            <div class="result-field">

                <label>
                    DOCUMENT TYPE
                </label>

                <strong>
                    ${escapeHtml(
                        displayName
                    )}
                </strong>

            </div>

            ${fieldsHTML}

        </div>


        ${confidenceHTML}


        ${errorHTML}

    `;


    result.classList.remove(
        "hidden"
    );


    // -----------------------------------------------------
    // SMOOTH SCROLL
    // -----------------------------------------------------

    setTimeout(() => {

        result.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    }, 100);

}


// =========================================================
// FORMAT DOCUMENT TYPE
// =========================================================

function formatDocumentType(
    documentType
) {

    const names = {

        aadhaar:
            "Aadhaar Card",

        pan:
            "PAN Card",

        passport:
            "Passport",

        driving_license:
            "Driving Licence",

        voter_id:
            "Voter ID",

        unknown:
            "Unknown Document"

    };


    return (
        names[documentType] ||
        documentType
            .replaceAll("_", " ")
            .replace(
                /\b\w/g,
                letter =>
                    letter.toUpperCase()
            )
    );
}


// =========================================================
// ERROR
// =========================================================

function showError(
    message
) {

    result.innerHTML = `

        <div class="error-result">

            <strong>
                VERIFICATION ERROR
            </strong>

            <br />
            <br />

            ${escapeHtml(
                message
            )}

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


// =========================================================
// HTML ESCAPING
// =========================================================

function escapeHtml(
    value
) {

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


// =========================================================
// KEYBOARD ACCESSIBILITY
// =========================================================

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