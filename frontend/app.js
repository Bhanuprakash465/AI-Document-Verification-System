/* =========================================================
   VERIFYAI - FRONTEND APPLICATION
   ========================================================= */

const API_URL = "/verify-document";

/* =========================================================
   DOM ELEMENTS
   ========================================================= */

const fileInput = document.getElementById("fileInput");
const chooseFileButton = document.getElementById("chooseFile");
const uploadPanel = document.getElementById("uploadPanel");
const uploadContent = document.getElementById("uploadContent");
const fileNameElement = document.getElementById("fileName");
const verifyButton = document.getElementById("verifyButton");

const resultSection = document.getElementById("result");
const resultGrid = document.getElementById("resultGrid");
const resultStatus = document.getElementById("resultStatus");
const resultErrors = document.getElementById("resultErrors");

const detectedDocumentElement =
    document.getElementById("detectedDocument");

const detectionConfidenceElement =
    document.getElementById("detectionConfidence");

/* =========================================================
   STATE
   ========================================================= */

let selectedFile = null;

/* =========================================================
   INITIAL STATE
   ========================================================= */

if (verifyButton) {
    verifyButton.disabled = true;
}

if (resultSection) {
    resultSection.classList.add("hidden");
}

/* =========================================================
   CHOOSE FILE
   ========================================================= */

if (chooseFileButton && fileInput) {
    chooseFileButton.addEventListener("click", () => {
        fileInput.click();
    });
}

/* =========================================================
   FILE SELECTED
   ========================================================= */

if (fileInput) {
    fileInput.addEventListener("change", (event) => {
        const files = event.target.files;

        if (!files || files.length === 0) {
            return;
        }

        handleSelectedFile(files[0]);
    });
}

/* =========================================================
   DRAG AND DROP
   ========================================================= */

if (uploadPanel) {

    uploadPanel.addEventListener("dragover", (event) => {

        event.preventDefault();

        uploadPanel.classList.add("dragging");
    });


    uploadPanel.addEventListener("dragleave", (event) => {

        event.preventDefault();

        uploadPanel.classList.remove("dragging");
    });


    uploadPanel.addEventListener("drop", (event) => {

        event.preventDefault();

        uploadPanel.classList.remove("dragging");

        const files = event.dataTransfer.files;

        if (!files || files.length === 0) {
            return;
        }

        handleSelectedFile(files[0]);
    });
}

/* =========================================================
   HANDLE SELECTED FILE
   ========================================================= */

function handleSelectedFile(file) {

    const allowedTypes = [
        "image/jpeg",
        "image/png",
        "application/pdf"
    ];

    const maxSize = 10 * 1024 * 1024;

    /* -----------------------------------------------------
       TYPE CHECK
       ----------------------------------------------------- */

    if (!allowedTypes.includes(file.type)) {

        showUploadError(
            "Only JPG, PNG and PDF files are supported."
        );

        resetFile();

        return;
    }


    /* -----------------------------------------------------
       SIZE CHECK
       ----------------------------------------------------- */

    if (file.size > maxSize) {

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
    }


    /* -----------------------------------------------------
       ENABLE VERIFY BUTTON
       ----------------------------------------------------- */

    if (verifyButton) {
        verifyButton.disabled = false;
    }


    /* -----------------------------------------------------
       CLEAR PREVIOUS RESULT
       ----------------------------------------------------- */

    if (resultSection) {
        resultSection.classList.add("hidden");
    }

    if (resultGrid) {
        resultGrid.innerHTML = "";
    }

    if (resultErrors) {
        resultErrors.innerHTML = "";
        resultErrors.classList.add("hidden");
    }
}

/* =========================================================
   UPLOAD ERROR
   ========================================================= */

function showUploadError(message) {

    if (!fileNameElement) {
        return;
    }

    fileNameElement.textContent =
        message.toUpperCase();

    fileNameElement.style.color = "#9b1c1c";
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
        fileNameElement.textContent = "";
        fileNameElement.style.color = "";
    }

    if (verifyButton) {
        verifyButton.disabled = true;
    }
}

/* =========================================================
   VERIFY DOCUMENT
   ========================================================= */

if (verifyButton) {

    verifyButton.addEventListener("click", async () => {

        if (!selectedFile) {
            return;
        }

        await verifyDocument();
    });
}

/* =========================================================
   MAIN VERIFICATION FUNCTION
   ========================================================= */

async function verifyDocument() {

    if (!selectedFile) {
        return;
    }


    /* -----------------------------------------------------
       BUTTON LOADING STATE
       ----------------------------------------------------- */

    verifyButton.disabled = true;

    const originalButtonHTML =
        verifyButton.innerHTML;

    verifyButton.innerHTML = `
        <span>PROCESSING DOCUMENT...</span>
        <span class="verify-arrow">↻</span>
    `;


    /* -----------------------------------------------------
       FORM DATA
       ----------------------------------------------------- */

    const formData = new FormData();

    formData.append(
        "file",
        selectedFile
    );


    try {

        /* -------------------------------------------------
           API REQUEST
           ------------------------------------------------- */

        const response = await fetch(
            API_URL,
            {
                method: "POST",
                body: formData
            }
        );


        /* -------------------------------------------------
           READ RESPONSE
           ------------------------------------------------- */

        let data = null;

        try {

            data = await response.json();

        } catch (jsonError) {

            throw new Error(
                "The server returned an invalid response."
            );
        }


        /* -------------------------------------------------
           HTTP ERROR
           ------------------------------------------------- */

        if (!response.ok) {

            let message =
                "Document verification failed.";

            if (data) {

                if (typeof data.detail === "string") {

                    message = data.detail;

                } else if (
                    data.detail &&
                    typeof data.detail.message === "string"
                ) {

                    message = data.detail.message;
                }
            }

            throw new Error(message);
        }


        /* -------------------------------------------------
           DISPLAY RESULT
           ------------------------------------------------- */

        renderVerificationResult(data);


    } catch (error) {

        console.error(
            "Verification error:",
            error
        );

        renderErrorResult(
            error.message ||
            "Unable to process the document."
        );


    } finally {

        /* -------------------------------------------------
           RESTORE BUTTON
           ------------------------------------------------- */

        verifyButton.disabled =
            !selectedFile;

        verifyButton.innerHTML =
            originalButtonHTML;
    }
}

/* =========================================================
   RENDER VERIFICATION RESULT
   ========================================================= */

function renderVerificationResult(data) {

    if (!resultSection) {
        return;
    }


    /* -----------------------------------------------------
       RESULT DATA
       ----------------------------------------------------- */

    const fields =
        data.fields || {};

    const documentInfo =
        data.document || {};

    const validation =
        data.validation || {};


    /* -----------------------------------------------------
       DOCUMENT TYPE
       ----------------------------------------------------- */

    const documentType =
        normalizeDocumentType(
            data.document_type ||
            documentInfo.document_type ||
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
        documentInfo.confidence;


    /* -----------------------------------------------------
       HEADER
       ----------------------------------------------------- */

    if (detectedDocumentElement) {

        detectedDocumentElement.textContent =
            displayName.toUpperCase();
    }


    if (detectionConfidenceElement) {

        if (
            typeof confidence === "number"
        ) {

            detectionConfidenceElement.textContent =
                `${Math.round(confidence * 100)}%`;

        } else {

            detectionConfidenceElement.textContent =
                "N/A";
        }
    }


    /* -----------------------------------------------------
       VALIDATION STATUS
       ----------------------------------------------------- */

    const isValid =
        validation.valid === true;


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
                : "REVIEW REQUIRED";
    }


    /* -----------------------------------------------------
       RESULT FIELDS
       ----------------------------------------------------- */

    renderFields(
        documentType,
        fields
    );


    /* -----------------------------------------------------
       VALIDATION ERRORS
       ----------------------------------------------------- */

    renderValidationErrors(
        validation
    );


    /* -----------------------------------------------------
       SHOW RESULT
       ----------------------------------------------------- */

    resultSection.classList.remove(
        "hidden"
    );


    /* -----------------------------------------------------
       SCROLL TO RESULT
       ----------------------------------------------------- */

    setTimeout(() => {

        resultSection.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    }, 100);
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
        normalized === "driving licence" ||
        normalized === "driving_license" ||
        normalized === "driving-license" ||
        normalized === "license"
    ) {

        return "driving_license";
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
        normalized === "aadhaar card" ||
        normalized === "aadhaar_card"
    ) {

        return "aadhaar";
    }


    if (
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
   RENDER FIELDS
   ========================================================= */

function renderFields(
    documentType,
    fields
) {

    if (!resultGrid) {
        return;
    }


    resultGrid.innerHTML = "";


    /* -----------------------------------------------------
       ALWAYS SHOW DOCUMENT TYPE
       ----------------------------------------------------- */

    addResultField(
        "DOCUMENT TYPE",
        getDocumentDisplayName(
            documentType
        )
    );


    /* =====================================================
       AADHAAR
       ===================================================== */

    if (documentType === "aadhaar") {

        addResultField(
            "FULL NAME",
            fields.name
        );

        addResultField(
            "AADHAAR NUMBER",
            fields.aadhaar_number
        );

        addResultField(
            "DATE OF BIRTH",
            fields.dob
        );

        addResultField(
            "GENDER",
            fields.gender
        );

        addResultField(
            "PIN CODE",
            fields.pin_code
        );

        addResultField(
            "ADDRESS",
            fields.address
        );

        return;
    }


    /* =====================================================
       PAN
       ===================================================== */

    if (documentType === "pan") {

        addResultField(
            "FULL NAME",
            fields.name
        );

        addResultField(
            "PAN NUMBER",
            fields.pan_number
        );

        addResultField(
            "FATHER NAME",
            fields.father_name
        );

        addResultField(
            "DATE OF BIRTH",
            fields.dob
        );

        return;
    }


    /* =====================================================
       PASSPORT
       ===================================================== */

    if (documentType === "passport") {

        addResultField(
            "PASSPORT NUMBER",
            fields.passport_number
        );

        addResultField(
            "SURNAME",
            fields.surname
        );

        addResultField(
            "GIVEN NAME",
            fields.given_name
        );

        addResultField(
            "FULL NAME",
            fields.name
        );

        addResultField(
            "NATIONALITY",
            fields.nationality
        );

        addResultField(
            "DATE OF BIRTH",
            fields.dob ||
            fields.date_of_birth
        );

        addResultField(
            "SEX",
            fields.sex ||
            fields.gender
        );

        addResultField(
            "PLACE OF BIRTH",
            fields.place_of_birth
        );

        addResultField(
            "PLACE OF ISSUE",
            fields.place_of_issue
        );

        addResultField(
            "DATE OF ISSUE",
            fields.date_of_issue
        );

        addResultField(
            "DATE OF EXPIRY",
            fields.date_of_expiry
        );

        return;
    }


    /* =====================================================
       VOTER ID
       ===================================================== */

    if (documentType === "voter_id") {

        addResultField(
            "FULL NAME",
            fields.name
        );

        addResultField(
            "VOTER ID",
            fields.voter_id ||
            fields.epic_number
        );

        addResultField(
            "DATE OF BIRTH",
            fields.dob
        );

        addResultField(
            "GENDER",
            fields.gender ||
            fields.sex
        );

        addResultField(
            "ADDRESS",
            fields.address
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

        addResultField(
            "FULL NAME",
            fields.name
        );

        addResultField(
            "LICENCE NUMBER",
            fields.licence_number ||
            fields.license_number
        );

        addResultField(
            "DATE OF BIRTH",
            fields.date_of_birth ||
            fields.dob
        );

        addResultField(
            "ISSUE DATE",
            fields.issue_date ||
            fields.date_of_issue
        );

        addResultField(
            "EXPIRY DATE",
            fields.expiry_date ||
            fields.date_of_expiry
        );

        addResultField(
            "BLOOD GROUP",
            fields.blood_group
        );

        addResultField(
            "VEHICLE CLASSES",
            formatVehicleClasses(
                fields.vehicle_classes
            )
        );

        addResultField(
            "ADDRESS",
            fields.address
        );

        return;
    }


    /* =====================================================
       UNKNOWN DOCUMENT
       ===================================================== */

    addResultField(
        "DOCUMENT STATUS",
        "Unsupported document type"
    );


    /* -----------------------------------------------------
       GENERIC FALLBACK
       ----------------------------------------------------- */

    Object.entries(fields)
        .forEach(([key, value]) => {

            if (
                key === "document_type" ||
                value === null ||
                value === undefined ||
                value === ""
            ) {
                return;
            }


            const alreadyShown =
                resultGrid.querySelector(
                    `[data-field="${key}"]`
                );


            if (alreadyShown) {
                return;
            }


            addResultField(
                formatLabel(key),
                formatValue(value),
                key
            );
        });
}

/* =========================================================
   ADD RESULT FIELD
   ========================================================= */

function addResultField(
    label,
    value,
    fieldKey = ""
) {

    if (!resultGrid) {
        return;
    }


    const field =
        document.createElement("div");


    field.className =
        "result-field";


    if (fieldKey) {

        field.dataset.field =
            fieldKey;
    }


    const labelElement =
        document.createElement("label");


    labelElement.textContent =
        label;


    const valueElement =
        document.createElement("strong");


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

        return value.join(", ");
    }


    if (
        typeof value === "object"
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

function formatLabel(
    key
) {

    return String(key)
        .replace(/_/g, " ")
        .replace(
            /\b\w/g,
            character =>
                character.toUpperCase()
        );
}

/* =========================================================
   FORMAT VEHICLE CLASSES
   ========================================================= */

function formatVehicleClasses(
    classes
) {

    if (!classes) {
        return "NOT DETECTED";
    }


    if (!Array.isArray(classes)) {

        return String(classes);
    }


    if (classes.length === 0) {

        return "NOT DETECTED";
    }


    return classes.join(", ");
}

/* =========================================================
   VALIDATION ERRORS
   ========================================================= */

function renderValidationErrors(
    validation
) {

    if (!resultErrors) {
        return;
    }


    resultErrors.innerHTML = "";


    const errors =
        Array.isArray(
            validation.errors
        )
            ? validation.errors
            : [];


    if (errors.length === 0) {

        resultErrors.classList.add(
            "hidden"
        );

        return;
    }


    resultErrors.classList.remove(
        "hidden"
    );


    const heading =
        document.createElement("strong");


    heading.textContent =
        "VALIDATION NOTES";


    resultErrors.appendChild(
        heading
    );


    const list =
        document.createElement("ul");


    list.style.marginTop =
        "12px";


    errors.forEach(error => {

        const item =
            document.createElement("li");


        item.textContent =
            String(error);


        list.appendChild(
            item
        );
    });


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


    if (detectedDocumentElement) {

        detectedDocumentElement.textContent =
            "PROCESSING ERROR";
    }


    if (detectionConfidenceElement) {

        detectionConfidenceElement.textContent =
            "N/A";
    }


    if (resultStatus) {

        resultStatus.classList.remove(
            "valid"
        );

        resultStatus.classList.add(
            "invalid"
        );

        resultStatus.textContent =
            "ERROR";
    }


    if (resultGrid) {

        resultGrid.innerHTML = "";

        addResultField(
            "STATUS",
            "DOCUMENT COULD NOT BE PROCESSED"
        );
    }


    if (resultErrors) {

        resultErrors.classList.remove(
            "hidden"
        );


        resultErrors.innerHTML = "";


        const errorBox =
            document.createElement("div");


        errorBox.className =
            "error-result";


        errorBox.textContent =
            message;


        resultErrors.appendChild(
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
   START VERIFICATION LINK
   ========================================================= */

document
    .querySelectorAll(
        'a[href="#upload"]'
    )
    .forEach(link => {

        link.addEventListener(
            "click",
            () => {

                setTimeout(() => {

                    if (uploadPanel) {

                        uploadPanel.scrollIntoView({
                            behavior: "smooth",
                            block: "center"
                        });
                    }

                }, 100);
            }
        );
    });

/* =========================================================
   SECURITY
   ========================================================= */

console.log(
    "VERIFYAI frontend initialized."
);