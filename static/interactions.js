<![CDATA[
    "use strict";
    var details, searchbtn, ignorecasebtn, unzoombtn, matchedtxt, svg, searching, currentSearchTerm, ignorecase, ignorecaseBtn;

    function init(evt) {
        details = document.getElementById("details").firstChild;
        searchbtn = document.getElementById("search");
        ignorecaseBtn = document.getElementById("ignorecase");
        unzoombtn = document.getElementById("unzoom");
        matchedtxt = document.getElementById("matched");
        svg = document.getElementsByTagName("svg")[0];
        searching = 0;
        currentSearchTerm = null;
        ignorecase = false;

        var params = get_params();
        if (params.x && params.y) {
            var target = document.querySelector('[x="' + params.x + '"][y="' + params.y + '"]');
            if (target) zoom(find_group(target));
        }
        if (params.s) search(params.s);
    }

    // ========== 点击事件处理 ==========
    window.addEventListener("click", function(e) {
        var target = find_group(e.target);

        // Reset Zoom 按钮
        if (e.target.id == "unzoom") {
            resetView();
            return;
        }

        // Search 按钮
        if (e.target.id == "search") {
            search_prompt();
            return;
        }

        // Ignore Case 按钮
        if (e.target.id == "ignorecase") {
            toggle_ignorecase();
            return;
        }

        // 火焰图元素点击
        if (target) {
            var depth = parseInt(target.getAttribute("data-depth"));

            // 点击 Node 层（depth=1）：缩放到该 Node
            if (depth === 1) {
                zoomToNode(target);
            }
            // 点击线程层（depth>=2）：不做处理
            else if (depth >= 2) {
                return;
            }
        }
    }, false);

    window.addEventListener("mouseover", function(e) {
        var target = find_group(e.target);
        if (target) details.nodeValue = g_to_text(target);
    }, false);

    window.addEventListener("mouseout", function(e) {
        var target = find_group(e.target);
        if (target) details.nodeValue = ' ';
    }, false);

    window.addEventListener("keydown", function(e) {
        if (e.keyCode === 114 || (e.ctrlKey && e.keyCode === 70)) {
            e.preventDefault();
            search_prompt();
        } else if (e.ctrlKey && e.keyCode === 73) {
            e.preventDefault();
            toggle_ignorecase();
        }
    }, false);

    // ========== 工具函数 ==========
    function get_params() {
        var params = {};
        var paramsarr = window.location.search.substr(1).split('&');
        for (var i = 0; i < paramsarr.length; ++i) {
            var tmp = paramsarr[i].split("=");
            if (!tmp[0] || !tmp[1]) continue;
            params[tmp[0]] = decodeURIComponent(tmp[1]);
        }
        return params;
    }

    function parse_params(params) {
        var uri = "?";
        for (var key in params) {
            uri += key + '=' + encodeURIComponent(params[key]) + '&';
        }
        if (uri.slice(-1) == "&") uri = uri.substring(0, uri.length - 1);
        if (uri == "?") uri = window.location.href.split('?')[0];
        return uri;
    }

    function find_child(node, selector) {
        return node.querySelector(selector);
    }

    function find_group(node) {
        var parent = node.parentElement;
        if (!parent) return;
        if (parent.id == "frames") return node;
        return find_group(parent);
    }

    function g_to_text(e) {
        var text = find_child(e, "title").firstChild.nodeValue;
        return text;
    }

    // ========== 缩放相关函数 ==========
    function zoom_reset(e) {
        if (e.attributes) {
            var x = e.getAttribute("_orig_x");
            if (x !== null) e.setAttribute("x", x);
            var w = e.getAttribute("_orig_width");
            if (w !== null) e.setAttribute("width", w);
        }
        if (e.childNodes) {
            for (var i = 0, c = e.childNodes; i < c.length; i++) {
                var child = c[i];
                if (child && child.nodeType === 1) {
                    zoom_reset(child);
                }
            }
        }
    }

    function zoom_child(e, x, ratio) {
        if (!e) return;
        var tagName = e.tagName;
        if (tagName === "rect" || tagName === "text") {
            var orig_x = e.getAttribute("x");
            var orig_width = e.getAttribute("width");
            if (orig_x !== null) {
                if (!e.hasAttribute("_orig_x")) e.setAttribute("_orig_x", orig_x);
                e.setAttribute("x", (parseFloat(orig_x) - x - 10) * ratio + 10);
                if (tagName === "text") {
                    var rect = find_child(e.parentNode, "rect[x]");
                    if (rect) e.setAttribute("x", parseFloat(rect.getAttribute("x")) + 3);
                }
            }
            if (orig_width !== null) {
                if (!e.hasAttribute("_orig_width")) e.setAttribute("_orig_width", orig_width);
                e.setAttribute("width", parseFloat(orig_width) * ratio);
            }
        }
        if (e.childNodes) {
            for (var i = 0, c = e.childNodes; i < c.length; i++) {
                var child = c[i];
                if (child && child.nodeType === 1) {
                    zoom_child(child, x - 10, ratio);
                }
            }
        }
    }

    function zoom_parent(e) {
        if (!e) return;
        var tagName = e.tagName;
        if (tagName === "rect" || tagName === "text") {
            var orig_x = e.getAttribute("x");
            var orig_width = e.getAttribute("width");
            if (orig_x !== null) {
                if (!e.hasAttribute("_orig_x")) e.setAttribute("_orig_x", orig_x);
                e.setAttribute("x", 10);
            }
            if (orig_width !== null) {
                if (!e.hasAttribute("_orig_width")) e.setAttribute("_orig_width", orig_width);
                e.setAttribute("width", parseInt(svg.getAttribute("width")) - 20);
            }
        }
        if (e.childNodes) {
            for (var i = 0, c = e.childNodes; i < c.length; i++) {
                var child = c[i];
                if (child && child.nodeType === 1) {
                    zoom_parent(child);
                }
            }
        }
    }

    // 点击 Node 层：隐藏其他 Node，显示该 Node 的线程
    function zoomToNode(node) {
        var targetNode = node.getAttribute("data-node");
        unzoombtn.classList.remove("hide");

        // 获取目标 Node 的位置和宽度
        var targetRect = find_child(node, "rect");
        if (!targetRect) return;

        var nodeX = parseFloat(targetRect.getAttribute("x"));
        var nodeWidth = parseFloat(targetRect.getAttribute("width"));

        // 计算缩放比例
        var totalWidth = parseFloat(svg.getAttribute("width")) - 20;
        var ratio = totalWidth / nodeWidth;

        var el = document.getElementById("frames").children;
        for (var i = 0; i < el.length; i++) {
            var e = el[i];
            var depth = parseInt(e.getAttribute("data-depth"));
            var elNode = e.getAttribute("data-node");

            if (depth === 1) {
                // Node 层：隐藏其他 Node，当前 Node 标记为 parent
                if (elNode === targetNode) {
                    e.classList.add("parent");
                    zoom_parent(e);
                    update_text(e);
                } else {
                    e.classList.add("hide");
                }
            } else if (depth === 2) {
                // 线程层：只显示当前 Node 的线程
                if (elNode === targetNode) {
                    e.classList.remove("hide");
                    zoom_child(e, nodeX, ratio);
                    update_text(e);
                } else {
                    e.classList.add("hide");
                }
            } else {
                // 其他层：隐藏
                e.classList.add("hide");
            }
        }
        search();
    }

    function zoom(node) {
        var rect = find_child(node, "rect");
        var width = parseFloat(rect.getAttribute("width"));
        var xmin = parseFloat(rect.getAttribute("x"));
        var xmax = parseFloat(xmin + width);
        var ratio = (parseFloat(svg.getAttribute("width")) - 20) / width;
        var fudge = 0.0001;

        unzoombtn.classList.remove("hide");

        var el = document.getElementById("frames").children;
        for (var i = 0; i < el.length; i++) {
            var e = el[i];
            var a = find_child(e, "rect").attributes;
            var ex = parseFloat(a.x.value);
            var ew = parseFloat(a.width.value);

            if (ex < xmin || ex + fudge >= xmax) {
                e.classList.add("hide");
            } else {
                zoom_child(e, xmin, ratio);
                update_text(e);
            }
        }
        search();
    }

    // 恢复初始状态
    function resetView() {
        unzoombtn.classList.add("hide");
        var el = document.getElementById("frames").children;
        for (var i = 0; i < el.length; i++) {
            el[i].classList.remove("parent");
            el[i].classList.remove("hide");
            zoom_reset(el[i]);
            update_text(el[i]);
        }
        search();

        // 清除 URL 参数
        var params = get_params();
        if (params.x) delete params.x;
        if (params.y) delete params.y;
        history.replaceState(null, null, parse_params(params));
    }

    // ========== 文本更新 ==========
    function update_text(e) {
        var r = find_child(e, "rect");
        var t = find_child(e, "text");

        // 如果没有 text 元素，直接返回
        if (!t || !r) return;

        var w = parseFloat(r.getAttribute("width")) - 3;

        // Try to get simplified name from comment
        var simplifiedName = null;
        var children = e.childNodes;
        for (var i = 0; i < children.length; i++) {
            if (children[i].nodeType === 8) { // Comment node
                var commentContent = children[i].nodeValue;
                if (commentContent.indexOf("simplified-name:") === 0) {
                    simplifiedName = commentContent.substring("simplified-name:".length);
                    break;
                }
            }
        }

        // Use simplified name if available, otherwise use title text
        var txt = simplifiedName || g_to_text(e).replace(/\([^(]*\)$/, "");
        t.setAttribute("x", parseFloat(r.getAttribute("x")) + 3);

        if (w < 2 * 12 * 0.59) {
            t.textContent = "";
            return;
        }

        t.textContent = txt;
        var sl = t.getSubStringLength(0, txt.length);
        if (/^ *$/.test(txt) || sl < w) return;

        var start = Math.floor((w/sl) * txt.length);
        for (var x = start; x > 0; x = x-2) {
            if (t.getSubStringLength(0, x + 2) <= w) {
                t.textContent = txt.substring(0, x) + "..";
                return;
            }
        }
        t.textContent = "";
    }

    // ========== 搜索功能 ==========
    function toggle_ignorecase() {
        ignorecase = !ignorecase;
        if (ignorecase) {
            ignorecaseBtn.classList.add("show");
        } else {
            ignorecaseBtn.classList.remove("show");
        }
        reset_search();
        search();
    }

    function reset_search() {
        var el = document.querySelectorAll("#frames rect");
        for (var i = 0; i < el.length; i++) {
            var orig_fill = el[i].getAttribute("_orig_fill");
            if (orig_fill !== null) el[i].setAttribute("fill", orig_fill);
        }
        var params = get_params();
        delete params.s;
        history.replaceState(null, null, parse_params(params));
    }

    function search_prompt() {
        if (!searching) {
            var term = prompt(
                "Enter a search term (regexp allowed, eg: ^ext4_)" +
                (ignorecase ? ", ignoring case" : "") +
                "\nPress Ctrl-i to toggle case sensitivity",
                ""
            );
            if (term != null) search(term);
        } else {
            reset_search();
            searching = 0;
            currentSearchTerm = null;
            searchbtn.classList.remove("show");
            searchbtn.firstChild.nodeValue = "Search";
            if (matchedtxt) {
                matchedtxt.classList.add("hide");
                matchedtxt.firstChild.nodeValue = "";
            }
        }
    }

    function search(term) {
        if (term) currentSearchTerm = term;
        if (currentSearchTerm === null) return;

        var re = new RegExp(currentSearchTerm, ignorecase ? 'i' : '');
        var el = document.getElementById("frames").children;
        var matches = {};
        var maxwidth = 0;
        for (var i = 0; i < el.length; i++) {
            var e = el[i];
            var func = g_to_text(e);
            var rect = find_child(e, "rect");
            if (func == null || rect == null) continue;

            var w = parseFloat(rect.getAttribute("width"));
            if (w > maxwidth) maxwidth = w;

            if (func.match(re)) {
                var x = parseFloat(rect.getAttribute("x"));
                var orig_fill = rect.getAttribute("fill");
                if (!rect.hasAttribute("_orig_fill")) rect.setAttribute("_orig_fill", orig_fill);
                rect.setAttribute("fill", "rgb(230,0,230)");

                if (matches[x] == undefined) {
                    matches[x] = w;
                } else {
                    if (w > matches[x]) matches[x] = w;
                }
                searching = 1;
            }
        }

        if (!searching) return;

        var params = get_params();
        params.s = currentSearchTerm;
        history.replaceState(null, null, parse_params(params));

        searchbtn.classList.add("show");
        searchbtn.firstChild.nodeValue = "Reset Search";

        var count = 0;
        var lastx = -1;
        var lastw = 0;
        var keys = [];
        for (var k in matches) {
            if (matches.hasOwnProperty(k)) keys.push(k);
        }
        keys.sort(function(a, b) { return a - b; });

        var fudge = 0.0001;
        for (var k in keys) {
            var x = parseFloat(keys[k]);
            var w = matches[keys[k]];
            if (x >= lastx + lastw - fudge) {
                count += w;
                lastx = x;
                lastw = w;
            }
        }

        if (matchedtxt) {
            matchedtxt.classList.remove("hide");
            var pct = 100 * count / maxwidth;
            if (pct != 100) pct = pct.toFixed(1);
            matchedtxt.firstChild.nodeValue = "Matched: " + pct + "%";
        }
    }
]]>
