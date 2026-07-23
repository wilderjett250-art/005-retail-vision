(function () {
  "use strict";

  var inspections = [
    { key: "license", code: "MODEL / LICENSE", title: "卷烟陈列面积占独立卷烟销售区域前柜总面积" },
    { key: "signboard", code: "MODEL / SIGNBOARD", title: "卷烟陈列面积占独立卷烟销售区域背柜总面积" },
    { key: "cabinet_module", code: "MODEL / CABINET MODULE", title: "亮证经营" },
    { key: "pillar", code: "MODEL / PILLAR", title: "店招类型" },
    { key: "pack_cluster", code: "MODEL / PACK CLUSTER", title: "卷烟经营专柜（前柜＋背柜）设施" }
  ];
  var states = {};
  var backendReady = false;
  var batchRunning = false;
  var urlApi = window.URL || window.webkitURL;

  function byId(id) { return document.getElementById(id); }
  function pad2(value) { return value < 10 ? "0" + value : String(value); }
  function itemNode(key) { return byId("item-" + key); }
  function setText(node, value) { node.innerText = value; }
  function hasClass(node, name) { return (" " + node.className + " ").indexOf(" " + name + " ") >= 0; }
  function addClass(node, name) { if (!hasClass(node, name)) node.className += " " + name; }
  function removeClass(node, name) { node.className = (" " + node.className + " ").replace(" " + name + " ", " ").replace(/^\s+|\s+$/g, ""); }
  function formatBytes(size) { return size < 1048576 ? Math.round(size / 1024) + " KB" : (size / 1048576).toFixed(1) + " MB"; }
  function safeFilename(name) { return name.replace(/[^\w\u4e00-\u9fff.-]+/g, "_").replace(/\.[^.]+$/, ""); }
  function detailFor(result, key) {
    if (!result || !result.score_details || !result.score_details[key]) return { score: 0, detected: false };
    return result.score_details[key];
  }

  function evaluationFor(result, key) {
    var direct = detailFor(result, key);
    if (key !== "pack_cluster") {
      return {
        detected: !!direct.detected,
        score: Number(direct.score || 0),
        classNames: [key],
        rule: "direct"
      };
    }

    var license = detailFor(result, "license");
    var signboard = detailFor(result, "signboard");
    var frontAndBackDetected = !!license.detected && !!signboard.detected;
    var classNames = [];
    var score = 0;
    if (direct.detected) {
      classNames.push("pack_cluster");
      score += Number(direct.score || 0);
    }
    if (frontAndBackDetected) {
      classNames.push("license");
      classNames.push("signboard");
      score += Number(license.score || 0) + Number(signboard.score || 0);
    }
    return {
      detected: !!direct.detected || frontAndBackDetected,
      score: score,
      classNames: classNames,
      rule: direct.detected ? "pack_cluster" : frontAndBackDetected ? "front_and_back" : "none"
    };
  }

  function evaluationMatchesClass(evaluation, className) {
    var index;
    for (index = 0; index < evaluation.classNames.length; index += 1) {
      if (evaluation.classNames[index] === className) return true;
    }
    return false;
  }

  function toast(message, isError) {
    var node = document.createElement("div");
    node.className = "toast" + (isError ? " error" : "");
    setText(node, message);
    byId("toast-region").appendChild(node);
    window.setTimeout(function () {
      if (node.parentNode) node.parentNode.removeChild(node);
    }, 3800);
  }

  function createItem(item, index) {
    var article = document.createElement("div");
    article.id = "item-" + item.key;
    article.className = "inspection-item";
    article.innerHTML =
      '<div class="item-heading clearfix">' +
        '<div class="item-index">' + pad2(index + 1) + '</div>' +
        '<div class="item-title"><p class="item-code">' + item.code + '</p><h2>' + item.title + '</h2></div>' +
        '<span class="item-state">等待图片</span>' +
      '</div>' +
      '<div class="workspace">' +
        '<div class="image-stage">' +
          '<div class="stage-label"><b>01</b>原始照片</div>' +
          '<input class="file-input" type="file" accept="image/jpeg,image/png,image/bmp,image/webp" style="display:none">' +
          '<div class="image-box source-box"><img alt="原始照片"><div class="empty-state"><button class="choose-button" type="button">选择图片</button><strong>选择对应检查照片</strong><small>支持拖放图片到此处</small></div></div>' +
          '<div class="file-meta"><span>尚未选择</span><button class="replace-file" type="button">重新选择</button></div>' +
        '</div>' +
        '<div class="flow">›</div>' +
        '<div class="image-stage">' +
          '<div class="stage-label"><b>02</b>标注结果</div>' +
          '<div class="image-box result-box"><img alt="标注结果"><div class="empty-state"><strong>等待检测</strong><small>结果将在这里显示</small></div></div>' +
          '<div class="file-meta"><span>模型标注图片</span><button class="download-result" type="button" disabled>保存结果图</button></div>' +
        '</div>' +
        '<div class="metrics">' +
          '<div class="metric-primary"><span>图片得分（total_score）</span><strong class="picture-score">—</strong></div>' +
          '<table><tr><th>本项结果</th><td class="target-result">—</td></tr><tr><th>细分值</th><td class="target-score">—</td></tr><tr><th>最高置信度</th><td class="target-confidence">—</td></tr><tr><th>目标数量</th><td class="detection-count">—</td></tr></table>' +
          '<button class="run-one" type="button" disabled>检测此项</button>' +
          '<button class="details-toggle" type="button">查看全部识别明细</button><div class="details-content">完成检测后显示</div>' +
        '</div>' +
      '</div>';
    byId("inspection-list").appendChild(article);

    var input = article.querySelector(".file-input");
    var sourceBox = article.querySelector(".source-box");
    article.querySelector(".choose-button").onclick = function () { input.click(); };
    article.querySelector(".replace-file").onclick = function () { input.click(); };
    input.onchange = function () { if (input.files && input.files[0]) selectFile(item.key, input.files[0]); };
    article.querySelector(".run-one").onclick = function () { runInference(item.key); };
    article.querySelector(".download-result").onclick = function () { downloadResult(item.key); };
    article.querySelector(".details-toggle").onclick = function () {
      var details = article.querySelector(".details-content");
      if (hasClass(details, "open")) removeClass(details, "open"); else addClass(details, "open");
    };
    sourceBox.ondragover = function (event) { event = event || window.event; if (event.preventDefault) event.preventDefault(); return false; };
    sourceBox.ondrop = function (event) {
      event = event || window.event;
      if (event.preventDefault) event.preventDefault();
      var files = event.dataTransfer && event.dataTransfer.files;
      if (files && files[0]) selectFile(item.key, files[0]);
      return false;
    };
  }

  function setItemStatus(key, status, text) {
    var state = states[key];
    state.status = status;
    var article = itemNode(key);
    article.className = "inspection-item" + (status === "empty" ? "" : " is-" + status);
    setText(article.querySelector(".item-state"), text);
    var button = article.querySelector(".run-one");
    button.disabled = !state.file || !backendReady || batchRunning || status === "running";
    setText(button, status === "running" ? "正在检测…" : "检测此项");
  }

  function selectFile(key, file) {
    var type = file.type || "";
    if (type.indexOf("image/") !== 0 && !/\.(jpe?g|png|bmp|webp)$/i.test(file.name || "")) {
      toast("请选择 JPG、PNG、BMP 或 WEBP 图片", true);
      return;
    }
    if (file.size > 35 * 1024 * 1024) {
      toast("单张图片不能超过 35 MB", true);
      return;
    }
    var state = states[key];
    if (state.resultUrl && urlApi) urlApi.revokeObjectURL(state.resultUrl);
    state.file = file;
    state.resultUrl = "";
    state.resultBlob = null;
    state.result = null;

    var article = itemNode(key);
    var reader = new FileReader();
    reader.onload = function (event) {
      article.querySelector(".source-box img").src = event.target.result;
      addClass(article.querySelector(".source-box"), "has-image");
    };
    reader.readAsDataURL(file);
    removeClass(article.querySelector(".result-box"), "has-image");
    article.querySelector(".result-box img").removeAttribute("src");
    setText(article.querySelector(".file-meta span"), file.name + " · " + formatBytes(file.size));
    resetMetrics(article);
    setItemStatus(key, "ready", "图片已选择");
    updateSummary();
  }

  function resetMetrics(article) {
    setText(article.querySelector(".picture-score"), "—");
    article.querySelector(".picture-score").className = "picture-score";
    setText(article.querySelector(".target-result"), "—");
    article.querySelector(".target-result").className = "target-result";
    setText(article.querySelector(".target-score"), "—");
    setText(article.querySelector(".target-confidence"), "—");
    setText(article.querySelector(".detection-count"), "—");
    setText(article.querySelector(".details-content"), "完成检测后显示");
    article.querySelector(".download-result").disabled = true;
  }

  function updateSummary() {
    var selected = 0, completed = 0, detected = 0, index, state;
    for (index = 0; index < inspections.length; index += 1) {
      state = states[inspections[index].key];
      if (state.file) selected += 1;
      if (state.status === "done") completed += 1;
      if (state.result && evaluationFor(state.result, inspections[index].key).detected) detected += 1;
      itemNode(inspections[index].key).querySelector(".run-one").disabled = !state.file || !backendReady || batchRunning || state.status === "running";
    }
    setText(byId("selected-count"), selected);
    setText(byId("completed-count"), completed);
    setText(byId("detected-count"), detected);
    byId("run-all").disabled = !backendReady || batchRunning || selected === 0;
    setText(byId("run-all"), batchRunning ? "正在检测…" : "检测全部");
    byId("export-report").disabled = completed === 0;
  }

  function runInference(key, callback) {
    var state = states[key];
    if (!state.file || !backendReady) { if (callback) callback(false); return; }
    var article = itemNode(key);
    setItemStatus(key, "running", "模型分析中");
    removeClass(article.querySelector(".result-box"), "has-image");
    updateSummary();

    var form = new FormData();
    form.append("file", state.file, state.file.name);
    var query = "conf_threshold=" + encodeURIComponent(Number(byId("confidence").value).toFixed(2)) + "&iou_threshold=" + encodeURIComponent(Number(byId("iou").value).toFixed(2));
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/infer?" + query, true);
    xhr.responseType = "blob";
    xhr.onload = function () {
      if (xhr.status < 200 || xhr.status >= 300) {
        setItemStatus(key, "error", "检测失败");
        toast(inspectionsByKey(key).title + "：推理服务返回 " + xhr.status, true);
        updateSummary();
        if (callback) callback(false);
        return;
      }
      try {
        var raw = xhr.getResponseHeader("X-Detection-Results") || "{}";
        state.result = JSON.parse(raw);
        state.resultBlob = xhr.response;
        if (state.resultUrl && urlApi) urlApi.revokeObjectURL(state.resultUrl);
        state.resultUrl = urlApi ? urlApi.createObjectURL(xhr.response) : "";
        if (state.resultUrl) article.querySelector(".result-box img").src = state.resultUrl;
        addClass(article.querySelector(".result-box"), "has-image");
        renderMetrics(key);
        var target = evaluationFor(state.result, key);
        setItemStatus(key, "done", target.detected ? "已识别" : "未识别到目标");
        updateSummary();
        if (callback) callback(true);
      } catch (error) {
        setItemStatus(key, "error", "结果解析失败");
        toast("结果解析失败：" + error.message, true);
        updateSummary();
        if (callback) callback(false);
      }
    };
    xhr.onerror = function () {
      setItemStatus(key, "error", "检测失败");
      toast("本地推理服务连接失败", true);
      updateSummary();
      if (callback) callback(false);
    };
    xhr.send(form);
  }

  function inspectionsByKey(key) {
    var index;
    for (index = 0; index < inspections.length; index += 1) if (inspections[index].key === key) return inspections[index];
    return inspections[0];
  }

  function renderMetrics(key) {
    var state = states[key];
    var article = itemNode(key);
    var result = state.result || {};
    var detections = result.detections || [];
    var target = evaluationFor(result, key);
    var matching = [], index, detection, name, confidence = 0;
    for (index = 0; index < detections.length; index += 1) {
      detection = detections[index];
      name = detection.class_name || detection.name || "";
      if (evaluationMatchesClass(target, name)) {
        matching.push(detection);
        confidence = Math.max(confidence, Number(detection.confidence || detection.score || 0));
      }
    }
    var totalScore = Number(result.total_score || 0);
    var pictureScore = article.querySelector(".picture-score");
    setText(pictureScore, totalScore.toFixed(2));
    pictureScore.className = "picture-score" + (totalScore > 0 ? " positive" : "");
    var targetResult = article.querySelector(".target-result");
    setText(targetResult, target.detected ? "识别通过" : "未识别到目标");
    targetResult.className = "target-result" + (target.detected ? " positive" : "");
    setText(article.querySelector(".target-score"), Number(target.score || 0).toFixed(2));
    setText(article.querySelector(".target-confidence"), matching.length ? (confidence * 100).toFixed(1) + "%" : "—");
    setText(article.querySelector(".detection-count"), String(matching.length));
    article.querySelector(".download-result").disabled = false;

    var details = article.querySelector(".details-content");
    details.innerHTML = "";
    for (index = 0; index < inspections.length; index += 1) {
      var item = inspections[index];
      var detail = evaluationFor(result, item.key);
      var row = document.createElement("div");
      row.className = "detail-row clearfix";
      row.innerHTML = "<span>" + item.key + "</span><b>" + (detail.detected ? "已识别" : "未识别") + " · " + Number(detail.score || 0).toFixed(2) + "</b>";
      details.appendChild(row);
    }
  }

  function runAll() {
    if (batchRunning) return;
    batchRunning = true;
    updateSummary();
    var index = 0, completed = 0;
    function next() {
      while (index < inspections.length && !states[inspections[index].key].file) index += 1;
      if (index >= inspections.length) {
        batchRunning = false;
        updateSummary();
        toast("批量检测完成，共处理 " + completed + " 张图片", false);
        return;
      }
      var key = inspections[index].key;
      index += 1;
      runInference(key, function (ok) { if (ok) completed += 1; next(); });
    }
    next();
  }

  function saveBlob(blob, filename) {
    if (window.navigator.msSaveOrOpenBlob) {
      window.navigator.msSaveOrOpenBlob(blob, filename);
      return;
    }
    var url = urlApi.createObjectURL(blob);
    var link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.setTimeout(function () { urlApi.revokeObjectURL(url); }, 1000);
  }

  function downloadResult(key) {
    var state = states[key];
    if (!state.resultBlob || !state.file) return;
    var index, order = 1;
    for (index = 0; index < inspections.length; index += 1) if (inspections[index].key === key) order = index + 1;
    saveBlob(state.resultBlob, pad2(order) + "_" + key + "_" + safeFilename(state.file.name) + "_result.jpg");
  }

  function clearAll() {
    var index, key, state, article;
    for (index = 0; index < inspections.length; index += 1) {
      key = inspections[index].key;
      state = states[key];
      if (state.resultUrl && urlApi) urlApi.revokeObjectURL(state.resultUrl);
      states[key] = { file: null, resultUrl: "", resultBlob: null, result: null, status: "empty" };
      article = itemNode(key);
      article.className = "inspection-item";
      setText(article.querySelector(".item-state"), "等待图片");
      removeClass(article.querySelector(".source-box"), "has-image");
      removeClass(article.querySelector(".result-box"), "has-image");
      article.querySelector(".source-box img").removeAttribute("src");
      article.querySelector(".result-box img").removeAttribute("src");
      article.querySelector(".file-input").value = "";
      setText(article.querySelector(".file-meta span"), "尚未选择");
      resetMetrics(article);
    }
    updateSummary();
  }

  function exportReport() {
    var report = {
      system: "现代零售终端智慧运营平台",
      exported_at: new Date().toISOString(),
      parameters: { confidence: Number(byId("confidence").value), iou: Number(byId("iou").value) },
      results: []
    };
    var index, item, state;
    for (index = 0; index < inspections.length; index += 1) {
      item = inspections[index];
      state = states[item.key];
      report.results.push({
        key: item.key,
        item: item.title,
        filename: state.file ? state.file.name : null,
        status: state.status,
        evaluation: state.result ? evaluationFor(state.result, item.key) : null,
        inference: state.result
      });
    }
    var blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json;charset=utf-8" });
    saveBlob(blob, "现代零售终端智慧运营平台检测结果_" + new Date().toISOString().slice(0, 10) + ".json");
  }

  function pollStatus() {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", "/api/status?_=" + new Date().getTime(), true);
    xhr.onload = function () {
      var node = byId("service-status");
      try {
        var status = JSON.parse(xhr.responseText || "{}");
        backendReady = !!status.backend_ready;
        node.className = "service-status " + (backendReady ? "is-ready" : status.status === "error" ? "is-error" : "is-loading");
        setText(node.getElementsByTagName("span")[0], backendReady ? "模型已就绪" : (status.message || "模型加载中"));
        updateSummary();
        if (!backendReady && status.status !== "error") window.setTimeout(pollStatus, 1200);
      } catch (error) {
        backendReady = false;
        node.className = "service-status is-error";
        setText(node.getElementsByTagName("span")[0], "本地服务异常");
        updateSummary();
      }
    };
    xhr.onerror = function () {
      backendReady = false;
      byId("service-status").className = "service-status is-error";
      setText(byId("service-status").getElementsByTagName("span")[0], "本地服务已断开");
      updateSummary();
    };
    xhr.send(null);
  }

  function shutdownApp() {
    if (!window.confirm("确认退出程序？当前本地推理服务将关闭。")) return;
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/shutdown", true);
    xhr.onload = function () { document.body.innerHTML = '<div style="padding:80px;text-align:center;font-size:24px">程序已退出，可以关闭此页面。</div>'; };
    xhr.send(null);
  }

  var index;
  for (index = 0; index < inspections.length; index += 1) {
    states[inspections[index].key] = { file: null, resultUrl: "", resultBlob: null, result: null, status: "empty" };
    createItem(inspections[index], index);
  }
  byId("run-all").onclick = runAll;
  byId("clear-all").onclick = function () {
    var hasFiles = false;
    for (var i = 0; i < inspections.length; i += 1) if (states[inspections[i].key].file) hasFiles = true;
    if (!hasFiles || window.confirm("确认清空已选择的图片和检测结果？")) clearAll();
  };
  byId("export-report").onclick = exportReport;
  byId("confidence").onchange = byId("confidence").oninput = function () { setText(byId("confidence-value"), Number(this.value).toFixed(2)); };
  byId("iou").onchange = byId("iou").oninput = function () { setText(byId("iou-value"), Number(this.value).toFixed(2)); };
  byId("exit-app").onclick = shutdownApp;
  pollStatus();
  updateSummary();
}());
