// ==============================================================================
// Google Apps Script (Code.gs) for Animew Pro & VIP DRAMA Cloud Sync & VIP Members
// Paste this code into: Extensions -> Apps Script in your Google Sheet
// ==============================================================================

const SHEET_NAME = "Manifest";
const VIP_SHEET_NAME = "VIP_Members";

// 🔒 Secure Backend Payment API Credentials (Server-side Only, Hidden from Users)
const PAYMENT_API_BASE = "https://mengsmm.store/api/v1/";
const PAYMENT_API_TOKEN = "05437beba0ad9d527bc874c5b83ff07ab7a299d70a363de940c2db98e05ef5ee";
const PAYMENT_ACCOUNT_ID = "leng_sheakmeng1@aclb";

function setupSheetIfNeeded(ss) {
  let sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
    sheet.appendRow([
      "ep_id", 
      "show_id", 
      "show_title", 
      "episode_number", 
      "telegram_message_id", 
      "telegram_file_id", 
      "file_size_mb", 
      "original_url", 
      "poster_url", 
      "source", 
      "updated_at",
      "json_payload"
    ]);
    sheet.getRange(1, 1, 1, 12).setFontWeight("bold").setBackground("#1e293b").setFontColor("#f8fafc");
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function setupVipSheetIfNeeded(ss) {
  let sheet = ss.getSheetByName(VIP_SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(VIP_SHEET_NAME);
    sheet.appendRow([
      "user_id",
      "username",
      "first_name",
      "plan_name",
      "amount",
      "currency",
      "payment_md5",
      "paid_at",
      "expires_at",
      "status"
    ]);
    sheet.getRange(1, 1, 1, 10).setFontWeight("bold").setBackground("#0f172a").setFontColor("#38bdf8");
    sheet.setFrozenRows(1);
  }
  return sheet;
}

// 🌐 GET API: Returns Manifest, Secure KHQR Proxy, or Checks VIP Member status
function doGet(e) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const action = e && e.parameter ? e.parameter.action : "";

    // 🔒 1. Secure Server-side KHQR Generator (Hides Token & Domain from Client)
    if (action === "generate_khqr") {
      const amount = encodeURIComponent(e.parameter.amount || "2.00");
      const url = `${PAYMENT_API_BASE}?type=generate_qr&amount=${amount}&currency=USD&api_token=${PAYMENT_API_TOKEN}`;
      const res = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
      const json = JSON.parse(res.getContentText());

      if (json.status === "success" && json.data) {
        return ContentService.createTextOutput(JSON.stringify({
          status: "success",
          data: {
            md5: json.data.md5,
            qr_string: json.data.qr || json.data.qr_string,
            qr_image: json.data.link_qr_code || json.data.qr_image_url,
            amount: json.data.amount,
            currency: json.data.currency,
            store_label: json.data.store_label || "LENG SHEAKMENG"
          }
        })).setMimeType(ContentService.MimeType.JSON);
      } else {
        return ContentService.createTextOutput(JSON.stringify(json))
          .setMimeType(ContentService.MimeType.JSON);
      }
    }

    // 🔒 2. Secure Server-side KHQR Payment Status Checker (Hides Token from Client)
    if (action === "check_khqr" && e.parameter.md5) {
      const md5 = encodeURIComponent(e.parameter.md5);
      const url = `${PAYMENT_API_BASE}?type=check_md5&md5=${md5}&api_token=${PAYMENT_API_TOKEN}`;
      const res = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
      const json = JSON.parse(res.getContentText());
      return ContentService.createTextOutput(JSON.stringify(json))
        .setMimeType(ContentService.MimeType.JSON);
    }

    // 👑 3. Check VIP Member Status by Telegram User ID
    if (action === "check_vip" && e.parameter.user_id) {
      const vipSheet = setupVipSheetIfNeeded(ss);
      const targetUserId = String(e.parameter.user_id).trim();
      const vipData = vipSheet.getDataRange().getValues();
      
      let isVip = false;
      let vipInfo = null;

      for (let i = 1; i < vipData.length; i++) {
        if (String(vipData[i][0]).trim() === targetUserId) {
          const expiresAt = new Date(vipData[i][8]);
          const now = new Date();
          if (expiresAt > now && vipData[i][9] === "ACTIVE") {
            isVip = true;
            vipInfo = {
              user_id: targetUserId,
              username: vipData[i][1],
              plan_name: vipData[i][3],
              amount: vipData[i][4],
              paid_at: vipData[i][7],
              expires_at: vipData[i][8],
              status: "ACTIVE"
            };
            break;
          }
        }
      }

      return ContentService.createTextOutput(JSON.stringify({
        is_vip: isVip,
        data: vipInfo
      })).setMimeType(ContentService.MimeType.JSON);
    }

    // Default: Return Full Drama Manifest
    const sheet = setupSheetIfNeeded(ss);
    const data = sheet.getDataRange().getValues();
    
    const manifest = {};
    for (let i = 1; i < data.length; i++) {
      const epId = String(data[i][0] || "").trim();
      const jsonStr = data[i][11]; // json_payload column
      
      if (epId && jsonStr) {
        try {
          manifest[epId] = JSON.parse(jsonStr);
        } catch (err) {
          manifest[epId] = {
            "show_id": String(data[i][1] || ""),
            "show_title": String(data[i][2] || ""),
            "episode_number": parseInt(data[i][3], 10) || 1,
            "telegram_message_id": parseInt(data[i][4], 10) || 0,
            "telegram_file_id": String(data[i][5] || ""),
            "file_size_mb": parseFloat(data[i][6]) || 0,
            "original_url": String(data[i][7] || ""),
            "poster_url": String(data[i][8] || ""),
            "source": String(data[i][9] || "dramaora"),
            "backed_up_at": String(data[i][10] || new Date().toISOString())
          };
        }
      }
    }
    
    return ContentService.createTextOutput(JSON.stringify(manifest))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ error: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// 📤 POST API: Receives new episode backup or VIP Payment Records
function doPost(e) {
  try {
    const rawContent = e.postData.contents;
    const body = JSON.parse(rawContent);
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    
    const now = new Date().toISOString();

    // 👑 Save VIP Member Payment Record into Google Sheet Tab "VIP_Members"
    if (body.action === "save_vip_member") {
      const vipSheet = setupVipSheetIfNeeded(ss);
      const userId = String(body.user_id || "").trim();
      const vipData = vipSheet.getDataRange().getValues();
      
      let foundRow = -1;
      for (let i = 1; i < vipData.length; i++) {
        if (String(vipData[i][0]).trim() === userId) {
          foundRow = i + 1;
          break;
        }
      }

      const rowData = [
        userId,
        body.username || "",
        body.first_name || "",
        body.plan_name || "គម្រោង VIP",
        body.amount || 2.00,
        body.currency || "USD",
        body.payment_md5 || "",
        body.paid_at || now,
        body.expires_at || new Date(Date.now() + 30 * 24 * 3600 * 1000).toISOString(),
        "ACTIVE"
      ];

      if (foundRow > 0) {
        vipSheet.getRange(foundRow, 1, 1, 10).setValues([rowData]);
      } else {
        vipSheet.appendRow(rowData);
      }

      return ContentService.createTextOutput(JSON.stringify({
        status: "success",
        action: "save_vip_member",
        user_id: userId,
        expires_at: rowData[8]
      })).setMimeType(ContentService.MimeType.JSON);
    }

    const sheet = setupSheetIfNeeded(ss);
    
    // Support Bulk Sync (all episodes in one ultra-fast batch)
    if (body.action === "bulk_sync" && body.manifest) {
      const allItems = body.manifest;
      const rows = [];
      Object.entries(allItems).forEach(([epId, item]) => {
        rows.push([
          epId,
          item.show_id || "",
          item.show_title || "",
          item.episode_number || 1,
          item.telegram_message_id || 0,
          item.telegram_file_id || "",
          item.file_size_mb || 0,
          item.original_url || "",
          item.poster_url || "",
          item.source || "dramaora",
          item.backed_up_at || now,
          JSON.stringify(item)
        ]);
      });
      
      const lastRow = sheet.getLastRow();
      if (lastRow > 1) {
        sheet.getRange(2, 1, lastRow - 1, 12).clearContent();
      }
      if (rows.length > 0) {
        sheet.getRange(2, 1, rows.length, 12).setValues(rows);
      }
      
      return ContentService.createTextOutput(JSON.stringify({
        status: "success",
        action: "bulk_sync",
        total: rows.length
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // 🗑️ Delete Entire Show (All episodes of a show)
    if (body.action === "delete_show" && (body.show_id || body.show_title)) {
      const targetShowId = String(body.show_id || "").trim();
      const targetTitle = String(body.show_title || "").trim();
      const data = sheet.getDataRange().getValues();
      let deletedCount = 0;
      
      for (let i = data.length - 1; i >= 1; i--) {
        const rowShowId = String(data[i][1]).trim();
        const rowTitle = String(data[i][2]).trim();
        if ((targetShowId && rowShowId === targetShowId) || (targetTitle && rowTitle === targetTitle)) {
          sheet.deleteRow(i + 1);
          deletedCount++;
        }
      }
      return ContentService.createTextOutput(JSON.stringify({
        status: "success",
        action: "delete_show",
        deleted_count: deletedCount,
        show_title: targetTitle
      })).setMimeType(ContentService.MimeType.JSON);
    }

    // 🗑️ Delete Single Episode
    if (body.action === "delete_episode" && body.ep_id) {
      const targetEpId = String(body.ep_id).trim();
      const data = sheet.getDataRange().getValues();
      let deleted = false;
      for (let i = data.length - 1; i >= 1; i--) {
        if (String(data[i][0]).trim() === targetEpId) {
          sheet.deleteRow(i + 1);
          deleted = true;
          break;
        }
      }
      return ContentService.createTextOutput(JSON.stringify({
        status: deleted ? "success" : "not_found",
        action: "delete_episode",
        ep_id: targetEpId
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // Single Episode Sync (Realtime from Python)
    const epId = String(body.ep_id || body.id || "").trim();
    const epData = body.data || body;
    
    if (!epId) {
      return ContentService.createTextOutput(JSON.stringify({ status: "error", message: "Missing ep_id" }))
        .setMimeType(ContentService.MimeType.JSON);
    }
    
    const data = sheet.getDataRange().getValues();
    let foundRow = -1;
    for (let i = 1; i < data.length; i++) {
      if (String(data[i][0]).trim() === epId) {
        foundRow = i + 1;
        break;
      }
    }
    
    const rowData = [
      epId,
      epData.show_id || "",
      epData.show_title || "",
      epData.episode_number || 1,
      epData.telegram_message_id || 0,
      epData.telegram_file_id || "",
      epData.file_size_mb || 0,
      epData.original_url || "",
      epData.poster_url || "",
      epData.source || "dramaora",
      epData.backed_up_at || now,
      JSON.stringify(epData)
    ];
    
    if (foundRow > 0) {
      sheet.getRange(foundRow, 1, 1, 12).setValues([rowData]);
    } else {
      sheet.appendRow(rowData);
    }
    
    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      ep_id: epId,
      show_title: epData.show_title,
      episode_number: epData.episode_number
    })).setMimeType(ContentService.MimeType.JSON);
    
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: err.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}
