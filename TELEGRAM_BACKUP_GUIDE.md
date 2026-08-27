# 🚀 ការណែនាំ Setup GitHub Actions Auto Backup to Telegram

ប្រព័ន្ធនេះនឹងដំណើរការទាញយកវីដេអូពី Database ហើយ Upload ចូលទៅកាន់ Private Telegram Channel របស់អ្នកដោយស្វ័យប្រវត្តិរៀងរាល់ ៦ ម៉ោងម្តង (ឬអាចចុច Run ដោយដៃគ្រប់ពេល)។

---

### ជំហានទី ១: យក Telegram Secrets

1. **Telegram API_ID & API_HASH**:
   - ចូលទៅកាន់គេហទំព័រ: [https://my.telegram.org](https://my.telegram.org)
   - Login លេខទូរស័ព្ទ Telegram របស់អ្នក
   - ចុចលើ **API development tools** រួចបង្កើត App មួយដើម្បីទទួលបាន `api_id` និង `api_hash`។
2. **Telegram BOT_TOKEN**:
   - បើក Telegram ស្វែងរក Bot ឈ្មោះ `@BotFather`
   - វាយ `/newbot` ដើម្បីបង្កើត Bot ថ្មី រួចចម្លងយក **API Token**។
3. **Private Channel ID**:
   - បង្កើត Private Channel មួយក្នុង Telegram
   - Add Bot របស់អ្នកចូលជា **Admin** ក្នុង Channel នោះ
   - យក Channel ID (ឧទាហរណ៍ `-1002234567890`)។

---

### ជំហានទី ២: ដាក់ Secrets ចូលក្នុង GitHub Repository

1. ចូលទៅកាន់ GitHub Repo របស់អ្នក
2. ចុចលើ **Settings** > **Secrets and variables** > **Actions**
3. ចុច **New repository secret** រួចបង្កើត ៤ នេះ៖
   - `TG_API_ID` : (លេខ api_id របស់អ្នក)
   - `TG_API_HASH` : (លេខ api_hash របស់អ្នក)
   - `TG_BOT_TOKEN` : (Bot Token ពី BotFather)
   - `TG_CHANNEL_ID` : (ID នៃ Telegram Channel របស់អ្នក)

---

### ជំហានទី ៣: ដំណើរការ (Run Backup)

* **ស្វ័យប្រវត្តិ (Automatic)**: GitHub Actions នឹងដំណើរការរៀងរាល់ ៦ ម៉ោងម្តងដោយខ្លួនឯង។
* **ចុច Run ដោយដៃ (Manual)**:
  - ចូលទៅកាន់ Tab **Actions** លើ GitHub
  - ជ្រើសរើស **Auto Backup to Telegram**
  - ចុចលើ **Run workflow** វានឹងដំណើរការ Backup ភ្លាមៗតែម្តង!
