/**
 * 漢検トレーニング ランキング用 Apps Script（英検トレーニングとは別のスプレッドシートに紐づける）
 *   シート「scores」 …1人（1端末）1行。ランキングの元データ
 *   シート「log」    …10問ごとの記録を1行ずつ追記
 *   シート「answers」…1問ごとの記録（日時・名前・問題番号・問題・正解・自分の答え・結果・秒数）
 *   シート「tags」   …1人1行。問題につけたタグ（⭐🔁❓📌💯）を JSON で保存（action: "tags"）
 * 同じニックネームを入れると、別の端末でも記録を引き継げる（action: "claim"）。
 */
const SCORES = "scores";
const LOG = "log";
const HEAD = ["uid","nick","totalOk","plays","q","best","updatedAt"];
const LOG_HEAD = ["at","uid","nick","ok","n","avg"];
const ANSWERS = "answers";
const ANS_HEAD = ["日時","名前","問題番号","問題","正解","自分の答え","結果","秒数","uid"];
const RESULTS = ["正解","ヒントで正解","まちがい"];
const DATE_FMT = "yyyy/MM/dd HH:mm";
const TAGS = "tags";
const TAGS_HEAD = ["uid","json","updatedAt"];
const TOP = 50;

function sheet_(name, head){
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(name);
  if(!sh){ sh = ss.insertSheet(name); sh.appendRow(head); sh.setFrozenRows(1); }
  return sh;
}
function out_(obj){ return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON); }
function int_(v){ const x = Math.floor(Number(v)); return isFinite(x) && x > 0 ? x : 0; }
function uid_(v){ const s = String(v || ""); return /^[A-Za-z0-9-]{8,64}$/.test(s) ? s : ""; }
// 制御文字を除いて16字まで。= + - @ で始まる名前は数式扱いされないよう ' を付ける
function nick_(v){
  let s = String(v || "").replace(/[\u0000-\u001f\u007f]/g, "").trim().slice(0, 16);
  if(/^[=+\-@]/.test(s)) s = "'" + s;
  return s;
}
function text_(v, max){
  let s = String(v == null ? "" : v).replace(/[\u0000-\u001f\u007f]/g, " ").trim().slice(0, max || 200);
  if(/^[=+\-@]/.test(s)) s = "'" + s;
  return s;
}
function readAll_(sh){
  const last = sh.getLastRow();
  if(last < 2) return [];
  return sh.getRange(2, 1, last - 1, HEAD.length).getValues().map((r, i) => {
    const o = { row: i + 2 }; HEAD.forEach((h, j) => o[h] = r[j]); return o;
  }).filter(o => o.uid);
}
function ranking_(rows, me){
  const sorted = rows.slice().sort((a, b) => (Number(b.totalOk) || 0) - (Number(a.totalOk) || 0));
  let myRank = null;
  const list = sorted.map(o => {
    const rank = 1 + sorted.filter(x => (Number(x.totalOk) || 0) > (Number(o.totalOk) || 0)).length;
    if(me && o.uid === me) myRank = rank;
    return { rank: rank, nick: String(o.nick || ""), totalOk: Number(o.totalOk) || 0, plays: Number(o.plays) || 0,
      q: Number(o.q) || 0, bestAvg: o.best === "" ? null : Number(o.best), me: !!me && o.uid === me };
  });
  return { ranking: list.filter((o, i) => i < TOP || o.me), myRank: myRank };
}
// その人の全部の記録（1問ごとの結果つき）
function history_(uid){
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const log = ss.getSheetByName(LOG), ans = ss.getSheetByName(ANSWERS);
  if(!log || log.getLastRow() < 2) return [];
  const plays = log.getRange(2, 1, log.getLastRow() - 1, LOG_HEAD.length).getValues().filter(r => r[1] === uid && r[0] instanceof Date);
  const items = {};
  if(ans && ans.getLastRow() >= 2){
    ans.getRange(2, 1, ans.getLastRow() - 1, ANS_HEAD.length).getValues().forEach(r => {
      if(r[8] !== uid || !(r[0] instanceof Date)) return;
      const k = r[0].getTime();
      (items[k] = items[k] || []).push({ id: String(r[2]), qs: String(r[3]), cor: String(r[4]), ans: String(r[5]), res: String(r[6]), t: r[7] === "" ? null : Number(r[7]) });
    });
  }
  return plays.reverse().map(r => ({
    at: r[0].toISOString(), mode: "kanken", ok: Number(r[3]) || 0, n: Number(r[4]) || 0,
    avg: r[5] === "" ? null : Number(r[5]), items: items[r[0].getTime()] || []
  }));
}
function tagsRow_(uid){
  const sh = sheet_(TAGS, TAGS_HEAD), last = sh.getLastRow();
  const vals = last < 2 ? [] : sh.getRange(2, 1, last - 1, 2).getValues();
  for(let i = 0; i < vals.length; i++) if(vals[i][0] === uid){
    let o = {}; try{ o = JSON.parse(vals[i][1] || "{}"); }catch(err){}
    return { sh: sh, row: i + 2, tags: o };
  }
  return { sh: sh, row: 0, tags: {} };
}
function tags_(uid, incoming){
  const r = tagsRow_(uid), cur = r.tags;
  if(incoming && typeof incoming === "object"){
    Object.keys(incoming).slice(0, 5000).forEach(k => {
      const v = incoming[k]; if(!v || typeof v !== "object") return;
      const t = Number(v.t) || 0, ids = Array.isArray(v.ids) ? v.ids.filter(x => /^[a-z]{1,10}$/.test(String(x))).slice(0, 10) : [];
      if(String(k).length > 400) return;
      if(!cur[k] || t > (Number(cur[k].t) || 0)) cur[k] = { ids: ids, t: t };
    });
    let json = JSON.stringify(cur);
    if(json.length > 45000){
      Object.keys(cur).filter(k => !cur[k].ids.length).sort((a, b) => cur[a].t - cur[b].t).forEach(k => { if(JSON.stringify(cur).length > 45000) delete cur[k]; });
      json = JSON.stringify(cur);
    }
    if(json.length <= 49000){
      if(r.row) r.sh.getRange(r.row, 2, 1, 2).setValues([[json, new Date()]]);
      else r.sh.appendRow([uid, json, new Date()]);
    }
  }
  return cur;
}
function doGet(e){
  const me = uid_(e && e.parameter && e.parameter.me);
  return out_(Object.assign({ ok: true }, ranking_(readAll_(sheet_(SCORES, HEAD)), me)));
}
function doPost(e){
  let p;
  try{ p = JSON.parse(e.postData.contents); }catch(err){ return out_({ ok: false, error: "bad_json" }); }
  const uid = uid_(p.uid);
  if(!uid) return out_({ ok: false, error: "bad_uid" });
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try{
    const sh = sheet_(SCORES, HEAD);
    const rows = readAll_(sh);
    let o = rows.find(x => x.uid === uid);
    const nick = nick_(p.nick);
    if(p.action === "claim"){
      const want = String(p.nick || "").trim().toLowerCase();
      const hits = rows.filter(x => want && String(x.nick).trim().toLowerCase() === want)
        .sort((a, b) => new Date(b.updatedAt || 0) - new Date(a.updatedAt || 0));
      if(!hits.length) return out_({ ok: true, found: false });
      const h = hits[0];
      return out_({ ok: true, found: true, uid: h.uid, nick: String(h.nick), totalOk: Number(h.totalOk) || 0, plays: Number(h.plays) || 0, history: history_(h.uid), tags: tags_(h.uid) });
    }
    if(p.action === "history") return out_({ ok: true, history: history_(uid) });
    if(p.action === "tags") return out_({ ok: true, tags: tags_(uid, p.tags) });
    if(p.action === "nick"){
      if(o){ sh.getRange(o.row, HEAD.indexOf("nick") + 1).setValue(nick); o.nick = nick.replace(/^'/, ""); }
      return out_(Object.assign({ ok: true, saved: !!o }, ranking_(rows, uid)));
    }
    if(p.action !== "score") return out_({ ok: false, error: "bad_action" });
    const n = int_(p.n), ok = int_(p.ok);
    const avg = p.avg == null || !isFinite(Number(p.avg)) ? null : Math.round(Number(p.avg) * 10) / 10;
    if(!o){ o = { row: sh.getLastRow() + 1, uid: uid, nick: "", totalOk: 0, plays: 0, q: 0, best: "" }; rows.push(o); }
    if(nick) o.nick = nick;
    o.totalOk = (Number(o.totalOk) || 0) + ok;
    o.plays = (Number(o.plays) || 0) + 1;
    o.q = (Number(o.q) || 0) + n;
    // ベスト＝全問正解かつ5問以上の回の、正解した問題の平均秒数の最小
    if(ok === n && n >= 5 && avg != null && (o.best === "" || o.best == null || avg < Number(o.best))) o.best = avg;
    o.updatedAt = new Date();
    sh.getRange(o.row, 1, 1, HEAD.length).setValues([HEAD.map(h => o[h] === undefined ? "" : o[h])]);
    o.nick = String(o.nick).replace(/^'/, "");
    const now = new Date();
    const log = sheet_(LOG, LOG_HEAD);
    log.appendRow([now, uid, nick, ok, n, avg == null ? "" : avg]);
    log.getRange(log.getLastRow(), 1).setNumberFormat(DATE_FMT);
    const items = Array.isArray(p.items) ? p.items.slice(0, 50) : [];
    if(items.length){
      const ans = sheet_(ANSWERS, ANS_HEAD), start = ans.getLastRow() + 1;
      ans.getRange(start, 1, items.length, ANS_HEAD.length).setValues(items.map(it => [
        now, text_(o.nick || "名無し", 20), text_(it && it.id, 40), text_(it && it.qs), text_(it && it.cor), text_(it && it.ans),
        RESULTS.indexOf(it && it.res) >= 0 ? it.res : "まちがい",
        isFinite(Number(it && it.t)) ? Math.round(Number(it.t) * 10) / 10 : "", uid
      ]));
      ans.getRange(start, 1, items.length, 1).setNumberFormat(DATE_FMT);
    }
    return out_(Object.assign({ ok: true, totalOk: o.totalOk }, ranking_(rows, uid)));
  }finally{
    lock.releaseLock();
  }
}
