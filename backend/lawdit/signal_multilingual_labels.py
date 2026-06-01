"""Multilingual form-label matching for deterministic signal detection."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class MultilingualLabelRule:
    signal_type: str
    detector: str
    marker: str
    confidence: float
    tokens: tuple[str, ...]


MULTILINGUAL_LABEL_RULES = (
    MultilingualLabelRule(
        "organization_identifier",
        "multilingual_organization_label",
        "[REDACTED_ORGANIZATION]",
        0.7,
        ("公司", "单位", "组织", "empresa", "societe", "entreprise", "firma", "azienda", "bedrijf", "organisatie", "会社", "회사", "المؤسسة", "empresa proveedor"),
    ),
    MultilingualLabelRule(
        "person_name",
        "multilingual_person_label",
        "[REDACTED_PERSON_NAME]",
        0.8,
        ("姓名", "名字", "联系人", "负责人", "旅客", "乘客", "nombre completo", "nombre", "nom", "prenom", "vorname", "nachname", "reisender", "passagier", "nome", "naam", "imie", "nazwisko", "氏名", "お名前", "이름", "الاسم"),
    ),
    MultilingualLabelRule(
        "email",
        "multilingual_email_label",
        "[REDACTED_EMAIL]",
        0.86,
        ("邮箱", "电子邮件", "邮件", "correo electronico", "correo", "courriel", "e-mail", "メール", "이메일", "البريد الالكتروني", "البريد الإلكتروني"),
    ),
    MultilingualLabelRule(
        "phone_number",
        "multilingual_phone_label",
        "[REDACTED_PHONE]",
        0.84,
        ("电话", "手机号", "手机", "联系电话", "telefono", "telephone", "teléfono", "téléphone", "telefone", "telefoon", "telefon", "携帯", "電話", "전화", "الهاتف", "الجوال"),
    ),
    MultilingualLabelRule(
        "date_of_birth",
        "multilingual_birth_date_label",
        "[REDACTED_DATE_OF_BIRTH]",
        0.86,
        ("出生日期", "生日", "出生", "fecha de nacimiento", "date de naissance", "geburtsdatum", "data di nascita", "data de nascimento", "geboortedatum", "data urodzenia", "生年月日", "생년월일", "تاريخ الميلاد"),
    ),
    MultilingualLabelRule(
        "national_identifier",
        "multilingual_national_id_label",
        "[REDACTED_NATIONAL_ID]",
        0.86,
        ("身份证", "身份证号", "证件号码", "证件号", "dni", "nie", "cpf", "bsn", "pesel", "numero de identidad", "numéro d'identification", "numero d identification", "ausweisnummer", "マイナンバー", "주민등록번호", "رقم الهوية"),
    ),
    MultilingualLabelRule(
        "tax_id",
        "multilingual_tax_id_label",
        "[REDACTED_TAX_ID]",
        0.84,
        ("codice fiscale", "nif", "numero fiscal", "numero de identificacao fiscal", "steuer id", "steueridentifikation", "税番号", "납세자 번호", "الرقم الضريبي"),
    ),
    MultilingualLabelRule(
        "passport_number",
        "multilingual_passport_label",
        "[REDACTED_PASSPORT]",
        0.87,
        ("护照", "护照号", "护照号码", "pasaporte", "passeport", "reisepass", "passaporto", "paspoort", "paszport", "パスポート", "여권", "جواز السفر"),
    ),
    MultilingualLabelRule(
        "driver_license",
        "multilingual_driver_license_label",
        "[REDACTED_DRIVER_LICENSE]",
        0.84,
        ("驾驶证", "驾照", "驾驶证号", "驾照号码", "führerschein", "fuehrerschein", "licencia de conducir", "permiso de conducir", "permis de conduire", "patente di guida", "carta de condução", "rijbewijs", "운전면허", "運転免許"),
    ),
    MultilingualLabelRule(
        "signature",
        "multilingual_signature_label",
        "[REDACTED_SIGNATURE]",
        0.78,
        ("签名", "签字", "unterschrift", "assinatura", "署名", "서명", "التوقيع"),
    ),
    MultilingualLabelRule(
        "travel_record",
        "multilingual_travel_label",
        "[REDACTED_TRAVEL_RECORD]",
        0.76,
        ("预订编号", "订票号", "行程编号", "常旅客号", "buchungsnummer", "reservierungscode", "pnr", "numero de reserva", "numéro de réservation", "codice prenotazione", "旅程番号", "예약 번호"),
    ),
    MultilingualLabelRule(
        "address",
        "multilingual_address_label",
        "[REDACTED_ADDRESS]",
        0.79,
        ("地址", "住址", "家庭住址", "direccion", "dirección", "adresse", "anschrift", "indirizzo", "endereco", "endereço", "adres", "住所", "주소", "العنوان"),
    ),
    MultilingualLabelRule(
        "bank_account",
        "multilingual_bank_label",
        "[REDACTED_BANK_ACCOUNT]",
        0.84,
        ("银行账号", "银行账户", "账号", "cuenta bancaria", "compte bancaire", "bankkonto", "conto bancario", "conta bancaria", "bankrekening", "konto bankowe", "銀行口座", "계좌", "الحساب البنكي"),
    ),
    MultilingualLabelRule(
        "medical_identifier",
        "multilingual_medical_id_label",
        "[REDACTED_MEDICAL_ID]",
        0.86,
        ("病历号", "患者编号", "医保号", "numero de paciente", "dossier medical", "numéro patient", "patienten nummer", "numero paziente", "numero do paciente", "patientnummer", "患者番号", "رقم المريض"),
    ),
    MultilingualLabelRule(
        "health_data",
        "multilingual_health_label",
        "[REDACTED_HEALTH_DATA]",
        0.82,
        ("诊断", "病情", "过敏史", "diagnostico", "diagnóstico", "diagnostic", "diagnose", "diagnosi", "diagnoza", "allergie", "アレルギー", "진단", "التشخيص"),
    ),
    MultilingualLabelRule(
        "salary_compensation",
        "multilingual_compensation_label",
        "[REDACTED_COMPENSATION]",
        0.8,
        ("薪资", "工资", "奖金", "salario", "salaire", "gehalt", "bonus", "stipendio", "salario", "salaris", "wynagrodzenie", "給与", "급여", "الراتب"),
    ),
    MultilingualLabelRule(
        "credential_secret",
        "multilingual_secret_label",
        "[REDACTED_SECRET]",
        0.76,
        ("密码", "口令", "密钥", "令牌", "contrasena", "contraseña", "mot de passe", "passwort", "senha", "palavra passe", "wachtwoord", "haslo", "パスワード", "비밀번호", "كلمة المرور"),
    ),
)


def match_multilingual_label(label: str) -> MultilingualLabelRule | None:
    normalized = _normalize(label)
    for rule in MULTILINGUAL_LABEL_RULES:
        if any(_normalize(token) in normalized for token in rule.tokens):
            return rule
    return None


def multilingual_label_tokens() -> tuple[str, ...]:
    return tuple(token for rule in MULTILINGUAL_LABEL_RULES for token in rule.tokens)


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value).casefold()
    without_marks = "".join(character for character in decomposed if not unicodedata.combining(character))
    return " ".join(without_marks.replace("_", " ").replace("-", " ").split())
