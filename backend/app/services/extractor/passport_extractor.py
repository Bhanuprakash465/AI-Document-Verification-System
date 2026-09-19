"""
Robust Indian passport extractor.

Uses:
1. ICAO-style MRZ parsing as the primary source.
2. OCR label/value parsing as a secondary source.
3. OCR-tolerant labels.
4. Date ordering as a fallback for issue/expiry dates.
"""

import re
from datetime import datetime
from typing import Optional


DATE_PATTERN = re.compile(
    r"\b\d{2}[./-]\d{2}[./-]\d{4}\b"
)

MRZ_CHARS = re.compile(
    r"^[A-Z0-9<]{30,44}$"
)

PASSPORT_NUMBER_PATTERN = re.compile(
    r"\b[A-Z][0-9]{7}\b",
    re.IGNORECASE,
)


def clean_line(text: str) -> str:

    if not text:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(text),
    ).strip()


def compact(text: str) -> str:

    return re.sub(
        r"\s+",
        "",
        str(text or "").upper(),
    )


def clean_name(
    text: Optional[str],
) -> Optional[str]:

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

    if len(words) > 8:
        return None

    return text.upper()


def normalize_date(
    value: Optional[str],
) -> Optional[str]:

    if not value:
        return None

    match = DATE_PATTERN.search(
        value
    )

    if not match:
        return None

    value = match.group()

    value = value.replace(
        ".",
        "/",
    ).replace(
        "-",
        "/",
    )

    return value


def mrz_date(
    value: str,
) -> Optional[str]:

    if not re.fullmatch(
        r"\d{6}",
        value or "",
    ):
        return None

    try:

        dt = datetime.strptime(
            value,
            "%y%m%d",
        )

        return dt.strftime(
            "%d/%m/%Y"
        )

    except ValueError:

        return None


def _mrz_candidates(
    lines: list[str],
) -> list[str]:

    candidates = []

    for line in lines:

        value = compact(line)

        # Normal MRZ.
        if (
            MRZ_CHARS.fullmatch(value)
            and "<" in value
        ):
            candidates.append(value)
            continue

        # OCR may insert/remove a few spaces.
        if (
            len(value) >= 30
            and "<" in value
            and sum(
                c.isalnum() or c == "<"
                for c in value
            ) >= 28
        ):
            candidates.append(value)

    return candidates


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
        "mrz_line_1": None,
        "mrz_line_2": None,
    }

    candidates = _mrz_candidates(
        lines
    )

    if len(candidates) < 2:
        return result

    # Prefer the final two MRZ-looking lines.
    line1 = candidates[-2]
    line2 = candidates[-1]

    result["mrz_line_1"] = line1
    result["mrz_line_2"] = line2

    # =====================================================
    # LINE 2
    # ICAO TD3:
    #
    # 0-8   passport number
    # 9     check digit
    # 10-12 nationality
    # 13-18 DOB
    # 19    check digit
    # 20    sex
    # 21-26 expiry
    # 27    check digit
    # =====================================================

    if len(line2) >= 27:

        passport_number = line2[0:9]

        passport_number = (
            passport_number
            .replace("<", "")
        )

        # OCR sometimes reads O as 0 or vice versa.
        if re.fullmatch(
            r"[A-Z][0-9]{7}",
            passport_number,
        ):

            result[
                "passport_number"
            ] = passport_number

        nationality = line2[10:13]

        if re.fullmatch(
            r"[A-Z]{3}",
            nationality,
        ):

            result[
                "nationality"
            ] = nationality

        dob_raw = line2[13:19]

        dob = mrz_date(
            dob_raw
        )

        if dob:
            result[
                "date_of_birth"
            ] = dob

        sex = line2[20]

        if sex == "M":
            result["sex"] = "MALE"

        elif sex == "F":
            result["sex"] = "FEMALE"

        elif sex == "<":
            result["sex"] = None

        expiry_raw = line2[21:27]

        expiry = mrz_date(
            expiry_raw
        )

        if expiry:
            result[
                "date_of_expiry"
            ] = expiry

    # =====================================================
    # LINE 1 NAME - STRICT ICAO TD3
    #
    # P<IND<SURNAME<<GIVEN<NAMES
    #   0-1  type ("P" + A/Z or "<")
    #   2-4  issuing country (exactly 3 letters)
    #   5-43 name (SURNAME<<GIVEN<NAMES)
    #
    # If the type/country structure is malformed (e.g. specimen
    # cards or heavy OCR noise produce "P<<SPECIMEN..."), the MRZ
    # name field is UNRELIABLE: parsing it concatenates unrelated
    # tokens. In that case the raw MRZ lines are preserved but NO
    # name fields are fabricated - visual OCR parsing takes over.
    # =====================================================

    if (
        len(line1) >= 5
        and re.fullmatch(r"P[A-Z<]", line1[0:2])
        and re.fullmatch(r"[A-Z]{3}", line1[2:5])
    ):

        name_section = line1[5:44]

        parts = name_section.split(
            "<<",
            1,
        )

        surname_raw = parts[0].replace(
            "<",
            " ",
        ).strip()

        given_raw = (
            parts[1].replace(
                "<",
                " ",
            ).strip()
            if len(parts) == 2
            else ""
        )

        # Names must be pure A-Z runs - anything else means the
        # MRZ name field itself is corrupted.
        if re.fullmatch(
            r"[A-Z](?:[A-Z .']*[A-Z])?",
            surname_raw,
        ) and len(surname_raw) >= 2:
            result["surname"] = surname_raw

        if re.fullmatch(
            r"[A-Z](?:[A-Z .']*[A-Z])?",
            given_raw,
        ) and len(given_raw) >= 2:
            result["given_names"] = given_raw

    return result


def _find_value_after_label(
    lines: list[str],
    labels: tuple[str, ...],
) -> Optional[str]:

    for index, line in enumerate(lines):

        normalized = (
            line.lower()
            .replace(":", " ")
            .replace("-", " ")
        )

        for label in labels:

            if label in normalized:

                remainder = re.sub(
                    rf"(?i).*?{re.escape(label)}",
                    "",
                    line,
                )

                remainder = clean_line(
                    remainder
                )

                # A same-line remainder must contain at least 3
                # alphabetic characters. Shorter fragments (e.g.
                # "ls)" left over from a mangled label such as
                # "Given Namels)") are label debris, not values -
                # fall through to the following lines instead.
                if (
                    remainder
                    and sum(
                        character.isalpha()
                        for character in remainder
                    )
                    >= 3
                ):
                    return remainder

                # Search next two lines because
                # OCR often separates label/value.
                for offset in (
                    1,
                    2,
                ):

                    next_index = (
                        index + offset
                    )

                    if (
                        next_index
                        >= len(lines)
                    ):
                        continue

                    value = clean_line(
                        lines[next_index]
                    )

                    if value:
                        return value

    return None


def _find_date_after_label(
    lines: list[str],
    labels: tuple[str, ...],
) -> Optional[str]:

    for index, line in enumerate(lines):

        normalized = (
            line.lower()
        )

        if not any(
            label in normalized
            for label in labels
        ):
            continue

        # Same line.
        match = DATE_PATTERN.search(
            line
        )

        if match:
            return normalize_date(
                match.group()
            )

        # Next 3 OCR lines.
        for offset in (
            1,
            2,
            3,
        ):

            next_index = (
                index + offset
            )

            if (
                next_index
                >= len(lines)
            ):
                continue

            match = DATE_PATTERN.search(
                lines[next_index]
            )

            if match:
                return normalize_date(
                    match.group()
                )

    return None


def _all_dates(
    lines: list[str],
) -> list[str]:

    dates = []

    for line in lines:

        for match in DATE_PATTERN.finditer(
            line
        ):

            value = normalize_date(
                match.group()
            )

            if value and value not in dates:
                dates.append(value)

    return dates


def _parse_date(
    value: Optional[str],
) -> Optional[datetime]:

    if not value:
        return None

    try:

        return datetime.strptime(
            value,
            "%d/%m/%Y",
        )

    except ValueError:

        return None


def _infer_issue_expiry(
    fields: dict,
    lines: list[str],
) -> None:

    dates = _all_dates(
        lines
    )

    if not dates:
        return

    # If explicit extraction already found
    # both values, do nothing.
    if (
        fields.get("date_of_issue")
        and fields.get("date_of_expiry")
    ):
        return

    parsed = []

    for date in dates:

        dt = _parse_date(
            date
        )

        if dt:
            parsed.append(
                (
                    date,
                    dt,
                )
            )

    if not parsed:
        return

    parsed.sort(
        key=lambda item: item[1]
    )

    # Passport visible page normally contains
    # DOB, issue date and expiry date.
    #
    # If OCR loses the issue/expiry labels but
    # two later dates are available, use chronology.
    if len(parsed) >= 2:

        if not fields.get(
            "date_of_issue"
        ):

            fields[
                "date_of_issue"
            ] = parsed[-2][0]

        if not fields.get(
            "date_of_expiry"
        ):

            fields[
                "date_of_expiry"
            ] = parsed[-1][0]


def _label_indices(
    lines: list[str],
    labels: tuple[str, ...],
) -> list[int]:

    result = []

    for index, line in enumerate(lines):

        normalized = line.lower()

        if any(
            label in normalized
            for label in labels
        ):
            result.append(index)

    return result


def _dates_with_positions(
    lines: list[str],
) -> list[tuple[int, str]]:

    result = []

    for index, line in enumerate(lines):

        for match in DATE_PATTERN.finditer(line):

            value = normalize_date(
                match.group()
            )

            if value:
                result.append((index, value))

    return result


def _first_date_on_or_after(
    label_index: int,
    dated_lines: list[tuple[int, str]],
    window: int = 3,
) -> Optional[tuple[int, str]]:

    for line_index, value in dated_lines:

        if label_index <= line_index <= label_index + window:
            return (line_index, value)

    return None


def _extract_passport_dates(
    lines: list[str],
    mrz: dict,
) -> tuple[Optional[str], Optional[str], Optional[str], list[str]]:
    """
    Label-position-aware date extraction.

    Returns (dob, issue, expiry, conflict_warnings).

    Key behaviours:
      * a date is bound to the NEAREST label preceding it, never
        to "the first date in the document";
      * scrambled two-column layouts (OCR emits both dates after
        the expiry label) are recovered: if the issue label found
        no date but the expiry label did, and another date follows
        the expiry date, the first belongs to issue;
      * MRZ dates are a structured CROSS-CHECK: they fill gaps and
        disagreements are reported, never silently resolved.
    """

    warnings: list[str] = []

    dated_lines = _dates_with_positions(lines)

    dob_labels = _label_indices(
        lines,
        (
            "date of birth",
            "dateofbirth",
            "dob",
            "birth",
        ),
    )

    issue_labels = _label_indices(
        lines,
        (
            "date of issue",
            "dateofissue",
            "issue date",
            "date issued",
        ),
    )

    expiry_labels = _label_indices(
        lines,
        (
            "date of expiry",
            "dateofexpiry",
            "expiry date",
            "date of expiration",
            "expiration date",
        ),
    )

    # -----------------------------------------------------
    # DOB
    # -----------------------------------------------------

    dob = None

    for label_index in dob_labels:

        hit = _first_date_on_or_after(
            label_index,
            dated_lines,
        )

        if hit:
            dob = hit[1]
            break

    # -----------------------------------------------------
    # ISSUE
    # -----------------------------------------------------

    issue = None
    issue_hit = None

    for label_index in issue_labels:

        hit = _first_date_on_or_after(
            label_index,
            dated_lines,
        )

        if hit:
            issue_hit = hit
            issue = hit[1]
            break

    # -----------------------------------------------------
    # EXPIRY
    # -----------------------------------------------------

    expiry = None
    expiry_hit = None

    for label_index in expiry_labels:

        hit = _first_date_on_or_after(
            label_index,
            dated_lines,
        )

        if hit:
            expiry_hit = hit
            expiry = hit[1]
            break

    # -----------------------------------------------------
    # SCRAMBLED LAYOUT RECOVERY
    #
    # OCR frequently linearises the issue/expiry area so BOTH
    # dates appear after the "Date of Expiry" label:
    #
    #   ... Date of Issue
    #   ... Date of Expiry
    #   01/01/2013
    #   01/01/2023
    #
    # If the issue label found no date but the expiry label did,
    # and another date follows the expiry date, then the date
    # bound to the expiry label is actually the ISSUE date and
    # the following one is the EXPIRY date.
    # -----------------------------------------------------

    if issue is None and expiry_hit is not None:

        following = [
            (line_index, value)
            for line_index, value in dated_lines
            if line_index > expiry_hit[0]
        ]

        if following:
            issue = expiry_hit[1]
            expiry = following[0][1]

    # -----------------------------------------------------
    # DUPLICATE GUARD
    #
    # If issue and expiry resolved to the same date but another
    # distinct date exists later in the document, the later one
    # is the expiry (a passport cannot expire on its issue date).
    # -----------------------------------------------------

    if (
        issue is not None
        and expiry is not None
        and issue == expiry
        and expiry_hit is not None
    ):

        following_distinct = [
            value
            for line_index, value in dated_lines
            if line_index > expiry_hit[0]
            and value != issue
        ]

        if following_distinct:
            expiry = following_distinct[0]

    # -----------------------------------------------------
    # MRZ CROSS-CHECK
    #
    # MRZ fills gaps; disagreements produce warnings.
    # -----------------------------------------------------

    mrz_dob = mrz.get("date_of_birth")
    mrz_expiry = mrz.get("date_of_expiry")

    if dob is None and mrz_dob:
        dob = mrz_dob
    elif (
        dob is not None
        and mrz_dob is not None
        and dob != mrz_dob
    ):
        warnings.append(
            f"MRZ date of birth ({mrz_dob}) disagrees with "
            f"the visual date of birth ({dob}); the visual "
            "value was kept."
        )

    if expiry is None and mrz_expiry:
        expiry = mrz_expiry
    elif (
        expiry is not None
        and mrz_expiry is not None
        and expiry != mrz_expiry
    ):
        warnings.append(
            f"MRZ date of expiry ({mrz_expiry}) disagrees with "
            f"the visual date of expiry ({expiry}); the visual "
            "value was kept."
        )

    # -----------------------------------------------------
    # CHRONOLOGY SANITY
    #
    # dob < issue <= expiry must hold where the available dates
    # permit checking. A violation downgrades issue/expiry to the
    # chronological ordering of all seen dates when that produces
    # a consistent triple.
    # -----------------------------------------------------

    parsed_dob = _parse_date(dob)
    parsed_issue = _parse_date(issue)
    parsed_expiry = _parse_date(expiry)

    if (
        parsed_dob
        and parsed_issue
        and parsed_expiry
        and not (
            parsed_dob < parsed_issue <= parsed_expiry
        )
    ):

        chronological = sorted(
            (parsed_dob, parsed_issue, parsed_expiry)
        )

        warnings.append(
            "Extracted dates violated the expected order "
            "(birth < issue <= expiry); dates were re-ordered "
            "chronologically."
        )

        dob = chronological[0].strftime("%d/%m/%Y")
        issue = chronological[1].strftime("%d/%m/%Y")
        expiry = chronological[2].strftime("%d/%m/%Y")

    return dob, issue, expiry, warnings


def extract_passport_fields(
    ocr_text: list[str],
) -> dict:

    fields = {
        "document_type": "passport",

        "passport_number": None,

        "name": None,

        "surname": None,

        "given_names": None,

        "given_name": None,

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

    # =====================================================
    # MRZ FIRST
    # =====================================================

    mrz = _extract_mrz(
        lines
    )

    for key, value in mrz.items():

        if value:
            fields[key] = value

    # =====================================================
    # PASSPORT NUMBER FALLBACK
    # =====================================================

    if not fields[
        "passport_number"
    ]:

        match = PASSPORT_NUMBER_PATTERN.search(
            "\n".join(lines)
        )

        if match:
            fields[
                "passport_number"
            ] = match.group().upper()

    # =====================================================
    # DATES (label-position aware + MRZ cross-check)
    # =====================================================

    dob, issue_date, expiry_date, date_warnings = (
        _extract_passport_dates(
            lines,
            mrz,
        )
    )

    fields["date_of_birth"] = dob
    fields["dob"] = dob
    fields["date_of_issue"] = issue_date
    fields["date_of_expiry"] = expiry_date
    fields["date_warnings"] = date_warnings

    # =====================================================
    # NATIONALITY
    # =====================================================

    if mrz.get("nationality"):

        fields[
            "nationality"
        ] = mrz[
            "nationality"
        ]

    else:

        nationality = (
            _find_value_after_label(
                lines,
                (
                    "nationality",
                ),
            )
        )

        if nationality:

            nationality = re.sub(
                r"[^A-Za-z]",
                "",
                nationality,
            )

            if nationality:
                fields[
                    "nationality"
                ] = nationality.upper()

    # =====================================================
    # SEX
    # =====================================================

    if mrz.get("sex"):

        fields["sex"] = mrz["sex"]

    else:

        sex = _find_value_after_label(
            lines,
            (
                "sex",
                "gender",
            ),
        )

        if sex:

            value = sex.upper()

            if value.startswith(
                "M"
            ):
                fields["sex"] = "MALE"

            elif value.startswith(
                "F"
            ):
                fields["sex"] = "FEMALE"

    fields["gender"] = fields[
        "sex"
    ]

    # =====================================================
    # SURNAME
    # =====================================================

    if mrz.get("surname"):

        fields["surname"] = mrz[
            "surname"
        ]

    else:

        surname = (
            _find_value_after_label(
                lines,
                (
                    "surname",
                    "sumname",
                    "sumame",
                    "surnam",
                ),
            )
        )

        if surname:

            fields[
                "surname"
            ] = clean_name(
                surname
            )

    # =====================================================
    # GIVEN NAME
    # =====================================================

    if mrz.get("given_names"):

        fields[
            "given_names"
        ] = mrz[
            "given_names"
        ]

    else:

        given = (
            _find_value_after_label(
                lines,
                (
                    "given name",
                    "given names",
                    "givennames",
                ),
            )
        )

        if given:

            fields[
                "given_names"
            ] = clean_name(
                given
            )

    fields[
        "given_name"
    ] = fields[
        "given_names"
    ]

    # =====================================================
    # FULL NAME
    # =====================================================

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

    # =====================================================
    # PLACE OF BIRTH
    # =====================================================

    place = _find_value_after_label(
        lines,
        (
            "place of birth",
            "placeofbirth",
        ),
    )

    if place:

        fields[
            "place_of_birth"
        ] = clean_line(
            place
        ).upper()

    # =====================================================
    # PLACE OF ISSUE
    # =====================================================

    place = _find_value_after_label(
        lines,
        (
            "place of issue",
            "placeofissue",
        ),
    )

    if place:

        fields[
            "place_of_issue"
        ] = clean_line(
            place
        ).upper()

    return fields


def extract_fields(
    ocr_text: list[str],
) -> dict:

    return extract_passport_fields(
        ocr_text
    )