/*
 * editor.js
 *
 * 负责 Quill 富文本编辑器初始化。
 *
 * 重点流程：
 * 1. 用户在 Quill 里编辑正文；
 * 2. 用户选择图片时，JS 上传图片到 /admin/uploads/image；
 * 3. 后端返回图片地址；
 * 4. JS 把图片地址插入 Quill；
 * 5. 表单提交前，把 Quill 里的 HTML 写入隐藏 input。
 */

const editorElement = document.querySelector("#editor");
const formElement = document.querySelector("#article-form");
const contentInput = document.querySelector("#content-input");
const articleIdInput = document.querySelector("#article-id-input");
const wordCountElement = document.querySelector("#word-count");
const autosaveStatusElement = document.querySelector("#autosave-status");
const previewButton = document.querySelector("#preview-button");

if (editorElement && formElement && contentInput && articleIdInput) {
  const quill = new Quill("#editor", {
    theme: "snow",
    placeholder: "请输入文章正文，可以插入图片...",
    modules: {
      toolbar: {
        container: [
          [{ header: [1, 2, 3, false] }],
          ["bold", "italic", "underline"],
          [{ list: "ordered" }, { list: "bullet" }],
          ["link", "image"],
          ["clean"],
        ],
        handlers: {
          image: uploadImage,
        },
      },
    },
  });

  function uploadImage() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.click();

    input.onchange = async () => {
      const file = input.files[0];
      if (!file) {
        return;
      }

      const formData = new FormData();
      formData.append("image", file);

      const response = await fetch("/admin/uploads/image", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        alert("图片上传失败，请确认已经登录后台。");
        return;
      }

      const data = await response.json();
      const range = quill.getSelection(true);
      quill.insertEmbed(range.index, "image", data.url);
      quill.setSelection(range.index + 1);
    };
  }

  function syncContentToHiddenInput() {
    // Quill 的 root.innerHTML 就是正文 HTML。
    contentInput.value = quill.root.innerHTML;
  }

  function updateWordCount() {
    if (!wordCountElement) {
      return;
    }
    const text = (quill.getText() || "").trim();
    const compact = text.replace(/\s+/g, "");
    wordCountElement.textContent = String(compact.length);
  }

  function setAutosaveStatus(message, isError = false) {
    if (!autosaveStatusElement) {
      return;
    }
    autosaveStatusElement.textContent = message;
    autosaveStatusElement.style.color = isError ? "#b91c1c" : "#6b7280";
  }

  async function autosaveDraft() {
    syncContentToHiddenInput();
    const formData = new FormData(formElement);
    formData.set("article_id", articleIdInput.value || "0");
    setAutosaveStatus("自动保存中...");

    const response = await fetch("/admin/articles/autosave", {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      throw new Error("autosave failed");
    }
    const data = await response.json();
    if (data.article_id) {
      articleIdInput.value = String(data.article_id);
    }
    if (data.edit_url) {
      window.history.replaceState({}, "", data.edit_url);
      formElement.action = data.edit_url;
    }
    setAutosaveStatus(`已自动保存：${data.saved_at}`);
  }

  function debounce(fn, delayMs) {
    let timer = null;
    return function debounced(...args) {
      if (timer) {
        window.clearTimeout(timer);
      }
      timer = window.setTimeout(() => fn(...args), delayMs);
    };
  }

  const debouncedAutosave = debounce(async () => {
    try {
      await autosaveDraft();
    } catch (_error) {
      setAutosaveStatus("自动保存失败，请检查网络或登录状态。", true);
    }
  }, 1200);

  quill.on("text-change", () => {
    updateWordCount();
    debouncedAutosave();
  });

  const watchInputs = formElement.querySelectorAll("input, textarea, select");
  watchInputs.forEach((element) => {
    if (element.id === "content-input" || element.id === "article-id-input") {
      return;
    }
    element.addEventListener("input", debouncedAutosave);
    element.addEventListener("change", debouncedAutosave);
  });

  if (previewButton) {
    previewButton.addEventListener("click", async () => {
      try {
        syncContentToHiddenInput();
        const formData = new FormData(formElement);
        const response = await fetch("/admin/articles/preview", {
          method: "POST",
          body: formData,
        });
        if (!response.ok) {
          throw new Error("preview failed");
        }
        const html = await response.text();
        const previewWindow = window.open("", "_blank");
        if (!previewWindow) {
          alert("浏览器拦截了预览窗口，请允许弹窗后重试。");
          return;
        }
        previewWindow.document.open();
        previewWindow.document.write(html);
        previewWindow.document.close();
      } catch (_error) {
        alert("预览失败，请确认已登录后台。");
      }
    });
  }

  formElement.addEventListener("submit", () => {
    syncContentToHiddenInput();
  });

  updateWordCount();
  setAutosaveStatus("自动保存已开启");
}
