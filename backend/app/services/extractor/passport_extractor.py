"""
Indian Passport OCR extractor.

Handles:
- Passport number
- Surname
- Given names
- Full name
- Nationality
- Date of birth
- Sex
- Place of birth
- Place of issue
- Date of issue
- Date of expiry
- MRZ passport number fallback
"""

import re
from datetime import datetime
from typing import Optional


PASSPORT_NUMBER_PATTERN = re.compile(
    r"\b[A-Z][0-9]{7}\b",
    re.IGNORECASE,
)

DATE_PATTERN = re.compile(
    r"\b\d{2}[/-]\d{2}[/-]\d{4}\b"
)

MRZ_PATTERN = re.compile(
    r"[A-Z0-9<]{30,44}",
    re.IGNORECASE,
)


def clean_line(text: str) -> str:

    if not text:
        return ""

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def clean_name(text: str) -> Optional[str]:

    if not text:
        return None

    text = clean_line(text)

    text = re.sub(
        r"[^A-Za-z.\s'-]",
        " ",
        text,
    )

    text = clean_line(text)

    if not text:
        return None

    words = text.split()

    if len(words) < 1:
        return None

    if len(words) > 8:
        return None

    return text.upper()


def _next_value(
    lines: list[str],
    index: int,
) -> Optional[str]:

    if index + 1 >= len(lines):
        return None

    value = clean_line(
        lines[index + 1]
    )

    return value or None


def _extract_date_from_label(
    lines: list[str],
    keywords: tuple[str, ...],
) -> Optional[str]:

    for index, line in enumerate(lines):

        normalized = line.lower()

        if not any(
            keyword in normalized
            for keyword in keywords
        ):
            continue

        # Date on same line.
        match = DATE_PATTERN.search(line)

        if match:
            return match.group()

        # Date on following OCR line.
        if index + 1 < len(lines):

            match = DATE_PATTERN.search(
                lines[index + 1]
            )

            if match:
                return match.group()

    return None


def _extract_label_value(
    lines: list[str],
    keywords: tuple[str, ...],
) -> Optional[str]:

    for index, line in enumerate(lines):

        normalized = line.lower()

        matched_keyword = None

        for keyword in keywords:

            if keyword in normalized:

                matched_keyword = keyword
                break

        if not matched_keyword:
            continue

        value = re.sub(
            rf"(?i).*?{re.escape(matched_keyword)}"
            r"\s*[:\-]?\s*",
            "",
            line,
        ).strip()

        if value:
            return clean_line(value)

        value = _next_value(
            lines,
            index,
        )

        if value:
            return value

    return None


def _extract_mrz(
    lines: list[str],
) -> dict:

    result = {
        "passport_number": None,
        "surname": None,
        "given_names": None,
        "nationality": None,
        "date_of_birth": None,
        "sex": None,
        "date_of_expiry": None,
    }

    mrz_lines = []

    for line in lines:

        compact = re.sub(
            r"\s+",
            "",
            line.upper(),
        )

        if (
            "<" in compact
            and len(compact) >= 30
        ):
            mrz_lines.append(compact)

    if len(mrz_lines) < 2:
        return result

    # Passport MRZ normally has:
    #
    # P<INDSURNAME<<GIVEN<NAMES<<<<<<<<
    #
    # XXXXXXXX<0INDYYMMDDMYYMMDD...

    line1 = mrz_lines[-2]
    line2 = mrz_lines[-1]

    # ---------------------------------------------------------
    # Passport number
    # ---------------------------------------------------------

    if len(line2) >= 9:

        candidate = line2[:9]

        candidate = candidate.replace(
            "<",
            "",
        )

        if re.fullmatch(
            r"[A-Z][0-9]{7}",
            candidate,
        ):

            result["passport_number"] = candidate

    # ---------------------------------------------------------
    # Nationality
    # ---------------------------------------------------------

    if len(line2) >= 13:

        nationality = line2[10:13]

        if re.fullmatch(
            r"[A-Z]{3}",
            nationality,
        ):

            result["nationality"] = nationality

    # ---------------------------------------------------------
    # DOB
    # ---------------------------------------------------------

    if len(line2) >= 20:

        raw_dob = line2[13:19]

        if re.fullmatch(
            r"\d{6}",
            raw_dob,
        ):

            result["date_of_birth"] = (
                _mrz_date(raw_dob)
            )

    # ---------------------------------------------------------
    # Sex
    # ---------------------------------------------------------

    if len(line2) >= 21:

        sex = line2[20]

        if sex == "M":
            result["sex"] = "MALE"

        elif sex == "F":
            result["sex"] = "FEMALE"

    # ---------------------------------------------------------
    # Expiry
    # ---------------------------------------------------------

    if len(line2) >= 27:

        raw_expiry = line2[21:27]

        if re.fullmatch(
            r"\d{6}",
            raw_expiry,
        ):

            result["date_of_expiry"] = (
                _mrz_date(raw_expiry)
            )

    # ---------------------------------------------------------
    # Name
    # ---------------------------------------------------------

    if line1.startswith("P<"):

        name_section = line1[5:]

        parts = name_section.split(
            "<<",
            1,
        )

        if len(parts) == 2:

            surname = parts[0].replace(
                "<",
                " ",
            )

            given = parts[1].replace(
                "<",
                " ",
            )

            surname = clean_name(
                surname
            )

            given = clean_name(
                given
            )

            if surname:
                result["surname"] = surname

            if given:
                result["given_names"] = given

    return result


def _mrz_date(value: str) -> str:

    """
    Convert YYMMDD to DD/MM/YYYY.

    Passport MRZ dates use two-digit years.
    """

    try:

        date = datetime.strptime(
            value,
            "%y%m%d",
        )

        return date.strftime(
            "%d/%m/%Y"
        )

    except ValueError:

        return None


def extract_passport_fields(
    ocr_text: list[str],
) -> dict:

    fields = {

        "document_type": "passport",

        "passport_number": None,

        "name": None,

        "surname": None,

        "given_names": None,

        "nationality": None,

        "date_of_birth": None,

        "dob": None,

        "place_of_birth": None,

        "place_of_issue": None,

        "date_of_issue": None,

        "date_of_expiry": None,

        "sex": None,

        "gender": None,
    }

    lines = [

        clean_line(line)

        for line in ocr_text

        if line and line.strip()

    ]

    if not lines:
        return fields

    # =========================================================
    # MRZ
    # =========================================================

    mrz = _extract_mrz(
        lines
    )

    for key, value in mrz.items():

        if value:
            fields[key] = value

    # =========================================================
    # PASSPORT NUMBER FALLBACK
    # =========================================================

    if not fields["passport_number"]:

        match = PASSPORT_NUMBER_PATTERN.search(
            "\n".join(lines)
        )

        if match:

            fields["passport_number"] = (
                match.group().upper()
            )

    # =========================================================
    # DATE OF BIRTH
    # =========================================================

    visible_dob = _extract_date_from_label(
        lines,
        (
            "date of birth",
            "date of birth",
            "dob",
        ),
    )

    if visible_dob:

        fields["date_of_birth"] = visible_dob

    if fields["date_of_birth"]:

        fields["dob"] = (
            fields["date_of_birth"]
        )

    # =========================================================
    # DATE OF ISSUE
    # =========================================================

    visible_issue = _extract_date_from_label(
        lines,
        (
            "date of issue",
            "issue date",
        ),
    )

    if visible_issue:

        fields["date_of_issue"] = (
            visible_issue
        )

    # =========================================================
    # DATE OF EXPIRY
    # =========================================================

    visible_expiry = _extract_date_from_label(
        lines,
        (
            "date of expiry",
            "expiry date",
            "date of expiration",
        ),
    )

    if visible_expiry:

        fields["date_of_expiry"] = (
            visible_expiry
        )

    # =========================================================
    # NATIONALITY
    # =========================================================

    nationality = _extract_label_value(
        lines,
        (
            "nationality",
        ),
    )

    if nationality:

        nationality = re.sub(
            r"[^A-Za-z]",
            "",
            nationality,
        )

        if nationality:

            fields["nationality"] = (
                nationality.upper()
            )

    # =========================================================
    # SEX
    # =========================================================

    sex = _extract_label_value(
        lines,
        (
            "sex",
            "gender",
        ),
    )

    if sex:

        normalized = sex.upper()

        if normalized in {
            "M",
            "MALE",
        }:

            fields["sex"] = "MALE"

        elif normalized in {
            "F",
            "FEMALE",
        }:

            fields["sex"] = "FEMALE"

    # =========================================================
    # SURNAME
    # =========================================================

    surname = _extract_label_value(
        lines,
        (
            "surname",
        ),
    )

    if surname:

        surname = clean_name(
            surname
        )

        if surname:

            fields["surname"] = surname

    # =========================================================
    # GIVEN NAME
    # =========================================================

    given_names = _extract_label_value(
        lines,
        (
            "given name",
            "given names",
        ),
    )

    if given_names:

        given_names = clean_name(
            given_names
        )

        if given_names:

            fields["given_names"] = (
                given_names
            )

    # =========================================================
    # COMBINED NAME
    # =========================================================

    if (
        fields["given_names"]
        and fields["surname"]
    ):

        fields["name"] = (
            f"{fields['given_names']} "
            f"{fields['surname']}"
        )

    elif fields["given_names"]:

        fields["name"] = (
            fields["given_names"]
        )

    elif fields["surname"]:

        fields["name"] = (
            fields["surname"]
        )

    # =========================================================
    # GENERIC NAME FALLBACK
    # =========================================================

    if not fields["name"]:

        for index, line in enumerate(lines):

            normalized = line.lower()

            if "name" not in normalized:
                continue

            if (
                "surname" in normalized
                or "given" in normalized
            ):
                continue

            value = re.sub(
                r"(?i).*?\bname\b"
                r"\s*[:\-]?\s*",
                "",
                line,
            ).strip()

            candidate = clean_name(
                value
            )

            if candidate:

                fields["name"] = candidate
                break

            if index + 1 < len(lines):

                candidate = clean_name(
                    lines[index + 1]
                )

                if candidate:

                    fields["name"] = (
                        candidate
                    )

                    break

    # =========================================================
    # PLACE OF BIRTH
    # =========================================================

    place_of_birth = _extract_label_value(
        lines,
        (
            "place of birth",
        ),
    )

    if place_of_birth:

        fields["place_of_birth"] = (
            place_of_birth.upper()
        )

    # =========================================================
    # PLACE OF ISSUE
    # =========================================================

    place_of_issue = _extract_label_value(
        lines,
        (
            "place of issue",
        ),
    )

    if place_of_issue:

        fields["place_of_issue"] = (
            place_of_issue.upper()
        )

    # =========================================================
    # NORMALIZE GENDER ALIAS
    # =========================================================

    fields["gender"] = fields["sex"]

    return fields