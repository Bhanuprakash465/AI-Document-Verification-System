/* =========================================================
   VERIFYAI - FRONTEND APPLICATION
   ========================================================= */

"use strict";

const API_URL = "/verify-document";
const MAX_FILE_SIZE = 10 * 1024 * 1024;

const ALLOWED_TYPES = [
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/x-ms-bmp",
    "image/tiff",
    "application/pdf"
];

// Some browsers report an empty/unreliable MIME type for BMP and
// TIFF files, so the extension is also checked as a fallback -
// the backend performs the real validation either way.
const ALLOWED_EXTENSIONS = [
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tiff",
    ".tif",
    ".pdf"
];

function hasAllowedExtension(filename) {
    const lower = String(filename || "").toLowerCase();
    return ALLOWED_EXTENSIONS.some(ext => lower.endsWith(ext));
}

/* =========================================================
   PAGE LOADER
   ========================================================= */

window.addEventListener("load", () => {
    const loader = document.getElementById("page-loader");

    if (!loader) {
        return;
    }

    loader.classList.add("loaded");

    setTimeout(() => {
        loader.remove();
    }, 900);
});


/* =========================================================
   DOM ELEMENTS
   ========================================================= */

const fileInput =
    document.getElementById("file-input");

const chooseFileButton =
    document.getElementById("browse-button");

const uploadPanel =
    document.getElementById("upload-form");

const uploadContent =
    document.querySelector(".upload-content");

const fileNameElement =
    document.getElementById("file-name");

const verifyButton =
    document.getElementById("verify-button");

const resultSection =
    document.getElementById("result");


/* =========================================================
   STATE
   ========================================================= */

let selectedFile = null;
let originalVerifyButtonHTML = null;


/* =========================================================
   INITIALIZATION
   ========================================================= */

document.addEventListener("DOMContentLoaded", () => {

    initializeResultSection();
    initializeUpload();
    initializeNavigation();

    if (verifyButton) {
        verifyButton.disabled = true;

        originalVerifyButtonHTML =
            verifyButton.innerHTML;
    }

    console.log(
        "VERIFYAI frontend initialized."
    );
});


/* =========================================================
   RESULT SECTION INITIALIZATION
   ========================================================= */

function initializeResultSection() {

    if (!resultSection) {
        return;
    }

    resultSection.innerHTML = `
        <div class="result-header">
            <div>
                <span class="section-number">
                    04 / RESULT
                </span>

                <h2>
                    Verification
                    <span class="serif">result.</span>
                </h2>
            </div>

            <span
                id="resultStatus"
                class="result-status"
            >
                WAITING
            </span>
        </div>

        <div
            id="resultGrid"
            class="result-grid"
        ></div>

        <div
            id="resultErrors"
            class="result-errors hidden"
        ></div>
    `;

    resultSection.classList.add("hidden");
}


/* =========================================================
   RESULT DOM REFERENCES
   ========================================================= */

function getResultElements() {

    return {
        resultGrid:
            document.getElementById("resultGrid"),

        resultStatus:
            document.getElementById("resultStatus"),

        resultErrors:
            document.getElementById("resultErrors")
    };
}


/* =========================================================
   UPLOAD INITIALIZATION
   ========================================================= */

function initializeUpload() {

    if (chooseFileButton && fileInput) {

        chooseFileButton.addEventListener(
            "click",
            (event) => {

                event.preventDefault();

                fileInput.click();
            }
        );
    }


    if (fileInput) {

        fileInput.addEventListener(
            "change",
            (event) => {

                const files =
                    event.target.files;

                if (
                    !files ||
                    files.length === 0
                ) {
                    return;
                }

                handleSelectedFile(
                    files[0]
                );
            }
        );
    }


    if (uploadPanel) {

        uploadPanel.addEventListener(
            "dragover",
            (event) => {

                event.preventDefault();

                uploadPanel.classList.add(
                    "dragging"
                );
            }
        );


        uploadPanel.addEventListener(
            "dragleave",
            (event) => {

                event.preventDefault();

                if (
                    event.relatedTarget &&
                    uploadPanel.contains(
                        event.relatedTarget
                    )
                ) {
                    return;
                }

                uploadPanel.classList.remove(
                    "dragging"
                );
            }
        );


        uploadPanel.addEventListener(
            "drop",
            (event) => {

                event.preventDefault();

                uploadPanel.classList.remove(
                    "dragging"
                );

                const files =
                    event.dataTransfer.files;

                if (
                    !files ||
                    files.length === 0
                ) {
                    return;
                }

                handleSelectedFile(
                    files[0]
                );
            }
        );
    }


    if (verifyButton) {

        verifyButton.addEventListener(
            "click",
            async (event) => {

                event.preventDefault();

                if (!selectedFile) {
                    return;
                }

                await verifyDocument();
            }
        );
    }
}


/* =========================================================
   FILE VALIDATION
   ========================================================= */

function handleSelectedFile(file) {

    clearUploadError();

    if (!file) {
        return;
    }


    /* -----------------------------------------------------
       FILE TYPE
       ----------------------------------------------------- */

    if (
        !ALLOWED_TYPES.includes(file.type) &&
        !hasAllowedExtension(file.name)
    ) {

        showUploadError(
            "Only JPG, PNG, WEBP, BMP, TIFF and PDF files are supported."
        );

        resetFile();

        return;
    }


    /* -----------------------------------------------------
       FILE SIZE
       ----------------------------------------------------- */

    if (file.size > MAX_FILE_SIZE) {

        showUploadError(
            "The selected file is larger than 10 MB."
        );

        resetFile();

        return;
    }


    /* -----------------------------------------------------
       SAVE FILE
       ----------------------------------------------------- */

    selectedFile = file;


    /* -----------------------------------------------------
       DISPLAY FILE NAME
       ----------------------------------------------------- */

    if (fileNameElement) {

        fileNameElement.textContent =
            file.name.toUpperCase();

        fileNameElement.style.color =
            "";
    }


    /* -----------------------------------------------------
       ENABLE VERIFY BUTTON
       ----------------------------------------------------- */

    if (verifyButton) {
        verifyButton.disabled = false;
    }


    /* -----------------------------------------------------
       CLEAR OLD RESULT
       ----------------------------------------------------- */

    hideResult();
}


/* =========================================================
   UPLOAD ERROR
   ========================================================= */

function showUploadError(message) {

    if (!fileNameElement) {
        return;
    }

    fileNameElement.textContent =
        String(message).toUpperCase();

    fileNameElement.style.color =
        "#9b1c1c";
}


/* =========================================================
   CLEAR UPLOAD ERROR
   ========================================================= */

function clearUploadError() {

    if (!fileNameElement) {
        return;
    }

    fileNameElement.style.color =
        "";
}


/* =========================================================
   RESET FILE
   ========================================================= */

function resetFile() {

    selectedFile = null;

    if (fileInput) {
        fileInput.value = "";
    }

    if (fileNameElement) {

        fileNameElement.textContent =
            "NO FILE SELECTED";

        fileNameElement.style.color =
            "";
    }

    if (verifyButton) {
        verifyButton.disabled = true;
    }
}


/* =========================================================
   HIDE RESULT
   ========================================================= */

function hideResult() {

    if (!resultSection) {
        return;
    }

    resultSection.classList.add(
        "hidden"
    );

    const elements =
        getResultElements();

    if (elements.resultGrid) {
        elements.resultGrid.innerHTML = "";
    }

    if (elements.resultErrors) {

        elements.resultErrors.innerHTML =
            "";

        elements.resultErrors.classList.add(
            "hidden"
        );
    }
}


/* =========================================================
   VERIFY DOCUMENT
   ========================================================= */

async function verifyDocument() {

    if (!selectedFile) {
        return;
    }


    if (!verifyButton) {
        return;
    }


    /* -----------------------------------------------------
       LOADING STATE
       ----------------------------------------------------- */

    verifyButton.disabled = true;

    if (!originalVerifyButtonHTML) {

        originalVerifyButtonHTML =
            verifyButton.innerHTML;
    }

    verifyButton.innerHTML = `
        <span>
            PROCESSING DOCUMENT...
        </span>

        <span class="verify-arrow">
            ↻
        </span>
    `;


    /* -----------------------------------------------------
       FORM DATA
       ----------------------------------------------------- */

    const formData =
        new FormData();

    formData.append(
        "file",
        selectedFile
    );


    try {

        console.log(
            "Sending document to:",
            API_URL
        );


        /* -------------------------------------------------
           API REQUEST
           ------------------------------------------------- */

        const response =
            await fetch(
                API_URL,
                {
                    method: "POST",
                    body: formData
                }
            );


        console.log(
            "Verification response:",
            response.status
        );


        /* -------------------------------------------------
           RESPONSE
           ------------------------------------------------- */

        const contentType =
            response.headers.get(
                "content-type"
            ) || "";


        let data;


        if (
            contentType.includes(
                "application/json"
            )
        ) {

            data =
                await response.json();

        } else {

            const text =
                await response.text();

            throw new Error(
                text ||
                "The server returned an invalid response."
            );
        }


        /* -------------------------------------------------
           HTTP ERROR
           ------------------------------------------------- */

        if (!response.ok) {

            let message =
                "Document verification failed.";


            if (
                data &&
                typeof data.detail === "string"
            ) {

                message =
                    data.detail;

            } else if (
                data &&
                data.detail &&
                typeof data.detail.message ===
                    "string"
            ) {

                message =
                    data.detail.message;
            }


            throw new Error(
                message
            );
        }


        /* -------------------------------------------------
           RENDER RESULT
           ------------------------------------------------- */

        renderVerificationResult(
            data
        );


    } catch (error) {

        console.error(
            "Verification error:",
            error
        );


        renderErrorResult(
            error &&
            error.message
                ? error.message
                : "Unable to process the document."
        );


    } finally {

        verifyButton.disabled =
            !selectedFile;

        verifyButton.innerHTML =
            originalVerifyButtonHTML;
    }
}


/* =========================================================
   RENDER VERIFICATION RESULT
   ========================================================= */

function renderVerificationResult(data) {

    if (!resultSection) {
        return;
    }


    const elements =
        getResultElements();


    const resultGrid =
        elements.resultGrid;

    const resultStatus =
        elements.resultStatus;

    const resultErrors =
        elements.resultErrors;


    /* -----------------------------------------------------
       RESPONSE DATA
       ----------------------------------------------------- */

    const fields =
        data &&
        data.fields
            ? normalizeObject(data.fields)
            : {};


    const documentInfo =
        data &&
        data.document
            ? data.document
            : {};


    const validation =
        data &&
        data.validation
            ? data.validation
            : {};


    /* -----------------------------------------------------
       DOCUMENT TYPE
       ----------------------------------------------------- */

    const documentType =
        normalizeDocumentType(
            data.document_type ||
            documentInfo.document_type ||
            fields.document_type ||
            "unknown"
        );


    /* -----------------------------------------------------
       DOCUMENT DISPLAY NAME
       ----------------------------------------------------- */

    const displayName =
        documentInfo.display_name ||
        getDocumentDisplayName(
            documentType
        );


    /* -----------------------------------------------------
       CONFIDENCE
       ----------------------------------------------------- */

    const confidence =
        getConfidence(
            documentInfo,
            validation,
            data
        );


    /* -----------------------------------------------------
       RESULT STATUS
       ----------------------------------------------------- */

    const isValid =
        validation.valid === true;

    const isOcrFailure =
        validation.status === "ocr_failed";


    if (resultStatus) {

        resultStatus.classList.remove(
            "valid",
            "invalid"
        );

        resultStatus.classList.add(
            isValid
                ? "valid"
                : "invalid"
        );

        resultStatus.textContent =
            isValid
                ? "VALIDATED"
                : isOcrFailure
                    ? "NO TEXT DETECTED"
                    : "REVIEW REQUIRED";
    }


    /* -----------------------------------------------------
       RESULT FIELDS
       ----------------------------------------------------- */

    if (resultGrid) {

        resultGrid.innerHTML = "";


        addResultField(
            resultGrid,
            "DOCUMENT TYPE",
            displayName
        );


        addResultField(
            resultGrid,
            "DETECTION CONFIDENCE",
            confidence !== null
                ? `${Math.round(confidence * 100)}%`
                : "N/A"
        );


        renderDocumentFields(
            resultGrid,
            documentType,
            fields
        );
    }


    /* -----------------------------------------------------
       VALIDATION MESSAGES
       ----------------------------------------------------- */

    renderValidationMessages(
        resultErrors,
        validation
    );


    /* -----------------------------------------------------
       SHOW RESULT
       ----------------------------------------------------- */

    resultSection.classList.remove(
        "hidden"
    );


    /* -----------------------------------------------------
       SCROLL
       ----------------------------------------------------- */

    setTimeout(() => {

        resultSection.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    }, 100);
}


/* =========================================================
   GET CONFIDENCE
   ========================================================= */

function getConfidence(
    documentInfo,
    validation,
    data
) {

    const candidates = [
        documentInfo.confidence,
        validation.confidence,
        data.confidence
    ];


    for (
        const value of candidates
    ) {

        if (
            typeof value === "number" &&
            Number.isFinite(value)
        ) {

            return Math.max(
                0,
                Math.min(
                    1,
                    value
                )
            );
        }
    }


    return null;
}


/* =========================================================
   NORMALIZE DOCUMENT TYPE
   ========================================================= */

function normalizeDocumentType(type) {

    if (!type) {
        return "unknown";
    }


    const normalized =
        String(type)
            .toLowerCase()
            .trim();


    if (
        normalized === "aadhaar" ||
        normalized === "aadhar" ||
        normalized === "aadhaar card" ||
        normalized === "aadhaar_card"
    ) {

        return "aadhaar";
    }


    if (
        normalized === "pan" ||
        normalized === "pan card" ||
        normalized === "pan_card"
    ) {

        return "pan";
    }


    if (
        normalized === "passport"
    ) {

        return "passport";
    }


    if (
        normalized === "voter id" ||
        normalized === "voter_id" ||
        normalized === "voter-id" ||
        normalized === "epic"
    ) {

        return "voter_id";
    }


    if (
        normalized === "driving licence" ||
        normalized === "driving license" ||
        normalized === "driving_license" ||
        normalized === "driving-license" ||
        normalized === "license"
    ) {

        return "driving_license";
    }


    return normalized;
}


/* =========================================================
   DOCUMENT DISPLAY NAME
   ========================================================= */

function getDocumentDisplayName(
    documentType
) {

    const names = {

        aadhaar:
            "Aadhaar Card",

        pan:
            "PAN Card",

        passport:
            "Passport",

        voter_id:
            "Voter ID",

        driving_license:
            "Driving Licence",

        unknown:
            "Unknown Document"
    };


    return (
        names[documentType] ||
        "Unknown Document"
    );
}


/* =========================================================
   RENDER DOCUMENT FIELDS
   ========================================================= */

function renderDocumentFields(
    resultGrid,
    documentType,
    fields
) {

    if (!resultGrid) {
        return;
    }


    const shownFields =
        new Set([
            "document_type"
        ]);


    const add =
        (
            label,
            key,
            ...fallbackKeys
        ) => {

            const keys = [
                key,
                ...fallbackKeys
            ];


            let value = null;


            for (
                const currentKey
                of keys
            ) {

                if (
                    fields[currentKey] !==
                        undefined &&
                    fields[currentKey] !==
                        null &&
                    fields[currentKey] !==
                        ""
                ) {

                    value =
                        fields[currentKey];

                    shownFields.add(
                        currentKey
                    );

                    break;
                }
            }


            addResultField(
                resultGrid,
                label,
                value
            );
        };


    /* =====================================================
       AADHAAR
       ===================================================== */

    if (
        documentType ===
        "aadhaar"
    ) {

        add(
            "FULL NAME",
            "name"
        );

        add(
            "AADHAAR NUMBER",
            "aadhaar_number"
        );

        add(
            "DATE OF BIRTH",
            "dob",
            "date_of_birth"
        );

        add(
            "GENDER",
            "gender",
            "sex"
        );

        add(
            "PIN CODE",
            "pin_code"
        );

        add(
            "ADDRESS",
            "address"
        );

        return;
    }


    /* =====================================================
       PAN
       ===================================================== */

    if (
        documentType ===
        "pan"
    ) {

        add(
            "FULL NAME",
            "name"
        );

        add(
            "PAN NUMBER",
            "pan_number"
        );

        add(
            "FATHER NAME",
            "father_name"
        );

        add(
            "DATE OF BIRTH",
            "dob",
            "date_of_birth"
        );

        return;
    }


    /* =====================================================
       PASSPORT
       ===================================================== */

    if (
        documentType ===
        "passport"
    ) {

        add(
            "PASSPORT NUMBER",
            "passport_number"
        );

        add(
            "SURNAME",
            "surname"
        );

        add(
            "GIVEN NAME",
            "given_names",
            "given_name"
        );

        add(
            "FULL NAME",
            "name"
        );

        add(
            "NATIONALITY",
            "nationality"
        );

        add(
            "DATE OF BIRTH",
            "dob",
            "date_of_birth"
        );

        add(
            "SEX",
            "sex",
            "gender"
        );

        add(
            "PLACE OF BIRTH",
            "place_of_birth"
        );

        add(
            "PLACE OF ISSUE",
            "place_of_issue"
        );

        add(
            "DATE OF ISSUE",
            "date_of_issue"
        );

        add(
            "DATE OF EXPIRY",
            "date_of_expiry"
        );

        return;
    }


    /* =====================================================
       VOTER ID
       ===================================================== */

    if (
        documentType ===
        "voter_id"
    ) {

        add(
            "FULL NAME",
            "name"
        );

        add(
            "VOTER ID",
            "voter_id",
            "epic_number"
        );

        add(
            "DATE OF BIRTH",
            "dob",
            "date_of_birth"
        );

        add(
            "GENDER",
            "gender",
            "sex"
        );

        add(
            "ADDRESS",
            "address"
        );

        return;
    }


    /* =====================================================
       DRIVING LICENCE
       ===================================================== */

    if (
        documentType ===
        "driving_license"
    ) {

        add(
            "FULL NAME",
            "name"
        );

        add(
            "LICENCE NUMBER",
            "licence_number",
            "license_number"
        );

        add(
            "DATE OF BIRTH",
            "date_of_birth",
            "dob"
        );

        add(
            "ISSUE DATE",
            "issue_date",
            "date_of_issue"
        );

        add(
            "EXPIRY DATE",
            "expiry_date",
            "date_of_expiry"
        );

        add(
            "BLOOD GROUP",
            "blood_group"
        );

        add(
            "VEHICLE CLASSES",
            "vehicle_classes"
        );

        add(
            "ADDRESS",
            "address"
        );

        return;
    }


    /* =====================================================
       GENERIC / UNKNOWN
       ===================================================== */

    for (
        const [key, value]
        of Object.entries(fields)
    ) {

        if (
            key === "document_type" ||
            shownFields.has(key)
        ) {
            continue;
        }


        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {
            continue;
        }


        addResultField(
            resultGrid,
            formatLabel(key),
            value
        );
    }
}


/* =========================================================
   ADD RESULT FIELD
   ========================================================= */

function addResultField(
    resultGrid,
    label,
    value
) {

    if (!resultGrid) {
        return;
    }


    const field =
        document.createElement(
            "div"
        );

    field.className =
        "result-field";


    const labelElement =
        document.createElement(
            "label"
        );

    labelElement.textContent =
        label;


    const valueElement =
        document.createElement(
            "strong"
        );

    valueElement.textContent =
        formatValue(value);


    field.appendChild(
        labelElement
    );

    field.appendChild(
        valueElement
    );

    resultGrid.appendChild(
        field
    );
}


/* =========================================================
   FORMAT VALUE
   ========================================================= */

function formatValue(value) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {

        return "NOT DETECTED";
    }


    if (Array.isArray(value)) {

        if (value.length === 0) {
            return "NOT DETECTED";
        }

        return value
            .map(item =>
                formatValue(item)
            )
            .join(", ");
    }


    if (
        typeof value ===
        "object"
    ) {

        try {

            return JSON.stringify(
                value
            );

        } catch {

            return "NOT DETECTED";
        }
    }


    return String(value);
}


/* =========================================================
   FORMAT LABEL
   ========================================================= */

function formatLabel(key) {

    return String(key)
        .replace(
            /_/g,
            " "
        )
        .replace(
            /\b\w/g,
            character =>
                character.toUpperCase()
        );
}


/* =========================================================
   NORMALIZE OBJECT
   ========================================================= */

function normalizeObject(value) {

    if (
        !value ||
        typeof value !==
            "object"
    ) {

        return {};
    }


    return value;
}


/* =========================================================
   VALIDATION MESSAGES
   ========================================================= */

function renderValidationMessages(
    resultErrors,
    validation
) {

    if (!resultErrors) {
        return;
    }


    resultErrors.innerHTML =
        "";


    const errors =
        Array.isArray(
            validation.errors
        )
            ? validation.errors
            : [];


    const warnings =
        Array.isArray(
            validation.warnings
        )
            ? validation.warnings
            : [];


    if (
        errors.length === 0 &&
        warnings.length === 0
    ) {

        resultErrors.classList.add(
            "hidden"
        );

        return;
    }


    resultErrors.classList.remove(
        "hidden"
    );


    const heading =
        document.createElement(
            "strong"
        );

    heading.textContent =
        errors.length > 0
            ? "VALIDATION NOTES"
            : "VALIDATION WARNINGS";


    resultErrors.appendChild(
        heading
    );


    const list =
        document.createElement(
            "ul"
        );

    list.style.marginTop =
        "12px";


    errors.forEach(
        error => {

            const item =
                document.createElement(
                    "li"
                );

            item.textContent =
                String(error);

            list.appendChild(
                item
            );
        }
    );


    warnings.forEach(
        warning => {

            const item =
                document.createElement(
                    "li"
                );

            item.textContent =
                String(warning);

            list.appendChild(
                item
            );
        }
    );


    resultErrors.appendChild(
        list
    );
}


/* =========================================================
   ERROR RESULT
   ========================================================= */

function renderErrorResult(
    message
) {

    if (!resultSection) {
        return;
    }


    const elements =
        getResultElements();


    if (elements.resultStatus) {

        elements.resultStatus.classList.remove(
            "valid"
        );

        elements.resultStatus.classList.add(
            "invalid"
        );

        elements.resultStatus.textContent =
            "ERROR";
    }


    if (elements.resultGrid) {

        elements.resultGrid.innerHTML =
            "";

        addResultField(
            elements.resultGrid,
            "STATUS",
            "DOCUMENT COULD NOT BE PROCESSED"
        );
    }


    if (elements.resultErrors) {

        elements.resultErrors.classList.remove(
            "hidden"
        );

        elements.resultErrors.innerHTML =
            "";


        const errorBox =
            document.createElement(
                "div"
            );

        errorBox.className =
            "error-result";

        errorBox.textContent =
            String(message);


        elements.resultErrors.appendChild(
            errorBox
        );
    }


    resultSection.classList.remove(
        "hidden"
    );


    setTimeout(() => {

        resultSection.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    }, 100);
}


/* =========================================================
   NAVIGATION
   ========================================================= */

function initializeNavigation() {

    document
        .querySelectorAll(
            'a[href="#upload"]'
        )
        .forEach(
            link => {

                link.addEventListener(
                    "click",
                    () => {

                        setTimeout(
                            () => {

                                if (
                                    uploadPanel
                                ) {

                                    uploadPanel.scrollIntoView({
                                        behavior: "smooth",
                                        block: "center"
                                    });
                                }

                            },
                            100
                        );
                    }
                );
            }
        );
}


/* =========================================================
   GLOBAL ERROR PROTECTION
   ========================================================= */

window.addEventListener(
    "error",
    event => {

        console.error(
            "VERIFYAI frontend error:",
            event.error ||
            event.message
        );
    }
);


/* =========================================================
   END
   ========================================================= */

console.log(
    "VERIFYAI frontend ready."
);