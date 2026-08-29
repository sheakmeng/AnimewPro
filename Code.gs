// ==============================================================================
// Google Apps Script (Code.gs) for Animew Pro Cloud Sync
// Paste this code into: Extensions -> Apps Script in your Google Sheet
// ==============================================================================

const SHEET_NAME = "Manifest";

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

// 🌐 GET API: Returns all backed-up episodes as JSON for APK and Web App
function doGet(e) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
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

// 📤 POST API: Receives new episode backup from Python (Pydroid 3)
function doPost(e) {
  try {
    const rawContent = e.postData.contents;
    const body = JSON.parse(rawContent);
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = setupSheetIfNeeded(ss);
    
    const now = new Date().toISOString();
    
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
    
    // Single Episode Sync (Realtime from Pydroid 3)
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
