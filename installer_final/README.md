# PHASEINV2 — ملف التثبيت النهائي (Final Installer)

مُثبِّت Windows **واحد وجاهز للتسليم للعميل**، مبني من كود التطبيق الخاص بيوم
**2026-08-22** (الإصدار **4.6.0**). الملف يضم التطبيق كاملًا مُجمَّدًا (frozen):
Python runtime + كل المكتبات + الكود + كل الأصول (assets)، فمفيش أي مكتبة لازم
تتثبت يدويًا عشان التطبيق يشتغل.

هذه مجلد تثبيت **جديد بالكامل** (`installer_final/`) ومستقل عن المجلد القديم
`installer/` — القديم اُستُخدم للمراجعة فقط ولم يُعدَّل ولا يُعتمد عليه.

## الناتج النهائي

```
D:\PHASEINV2\dist\PHASEINV2_Setup.exe
```

هذا هو الملف الوحيد اللي تسلّمه للعميل.

## البناء بأمر واحد

```powershell
powershell -ExecutionPolicy Bypass -File "D:\PHASEINV2\InvoicesKSA_publish\installer_final\build.ps1"
```

> من 2026-10-21 (v4.15.0) البناء من `InvoicesKSA_publish` (مش `CRM_PYTHON_APP_STRUCTURE`
> القديم). نسخ المكتبات مثبّتة في `build-constraints.txt` (نفس بناء v4.14.0)، فالـ
> `.buildvenv` الجديدة بتطلع نفس الحزمة. أي تحديث لمكتبة يتعمل هناك عن قصد.

> ⚠️ لا تمرّر السكربت عبر `2>&1` على PowerShell 5.1: PyInstaller يكتب رسائل INFO
> على stderr، والـ redirect يحوّل كل سطر إلى `NativeCommandError` فيبلّغ عن فشل
> بينما البناء ناجح فعليًا. شغّله كما هو أعلاه.

يقوم السكربت بـ:

1. تحديد Python 3.11 و Inno Setup 6 تلقائيًا.
2. تنظيف ناتج البناء السابق (dist / build / Output).
3. إنشاء بيئة بناء معزولة وتثبيت `requirements.txt` + PyInstaller.
4. تجميد واجهة التطبيق → `dist\PHASEINV2\PHASEINV2.exe` (onedir، نافذة).
5. تجميد أداة الإعداد → `dist\phaseinv2-config.exe` (onefile، console).
6. التحقق من المكتبات و Qt و QtWebEngine و psycopg و cryptography والأصول
   وقوالب اليوم (v9/v10/v11 + phase-1) + اختبار تشغيل فعلي.
7. تصريف `setup.iss` عبر Inno Setup 6.
8. نسخ المُثبِّت إلى `D:\PHASEINV2\dist` وطباعة المسار والحجم و SHA-256.

المتطلبات على **جهاز البناء فقط**: Python 3.11 و Inno Setup 6.

## عند العميل — خطوة واحدة قبل التثبيت

**PostgreSQL غير مضمّن داخل المُثبِّت** (بقرارك: تثبته أنت يدويًا عند العميل).
ثبّت PostgreSQL أولًا، ثم شغّل `PHASEINV2_Setup.exe`.

المُثبِّت يسأل عن **وضع قاعدة البيانات**:

| الوضع | متى تختاره |
|------|-----------|
| **Local Mode** | PostgreSQL على **نفس الجهاز** (localhost). |
| **Internal Server Mode** | PostgreSQL على **جهاز/سيرفر آخر** على الشبكة (يُرفض localhost). |

القيم الافتراضية جاهزة ومطابقة لإعدادك:

- اسم قاعدة البيانات: `InvPhase2`
- المستخدم: `postgres`
- البورت: `5432`

المُثبِّت بعدها: يختبر الاتصال، ينشئ قاعدة البيانات **فقط لو مش موجودة** (لا يحذف
ولا يستبدل أبدًا)، يكتب ملف الاتصال المُشفَّر في
`C:\ProgramData\PHASEINV2\connection.json`، ويجهّز الـ schema + مستخدم Admin
والصلاحيات بشكل idempotent. كلمة مرور قاعدة البيانات لا تُكتب في أي سجل ولا على
سطر أوامر.

## بيانات ومسارات وقت التشغيل

- ملف الاتصال المُشفَّر: `C:\ProgramData\PHASEINV2\connection.json`
- سجلات التثبيت والتشغيل: `C:\ProgramData\PHASEINV2\logs`
- النسخ الاحتياطية التلقائية: المجلد الذي يختاره المستخدم (أو
  `C:\ProgramData\PHASEINV2\Backups` افتراضيًا). التطبيق يأخذ نسخة عند الفتح
  (مرة في اليوم) وعند الإغلاق.

## ملفات هذا المجلد

| الملف | الغرض |
|------|------|
| `build.ps1` | سكربت البناء بأمر واحد. |
| `setup.iss` | سكربت Inno Setup للمُثبِّت الموحّد (محلي + شبكة). |
| `app.spec` | مواصفات PyInstaller لواجهة التطبيق (onedir). |
| `config.spec` | مواصفات PyInstaller لأداة الإعداد (onefile). |
| `build-constraints.txt` | النسخ المثبّتة للمكتبات وقت البناء (`pip -c`). |
| `entrypoints\app_main.py` | نقطة دخول واجهة التطبيق المُجمَّدة. |
| `entrypoints\config_main.py` | نقطة دخول أداة الإعداد المُجمَّدة. |

## ملاحظة عن الترقية

`AppId` ثابت (نفس المُعرِّف)، فتثبيت هذا الإصدار فوق تثبيت قديم على جهاز العميل
**يرقّيه في مكانه** بدل ما ينشئ نسخة ثانية جنبه.
