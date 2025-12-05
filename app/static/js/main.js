document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".shelf-nav").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const targetSelector = btn.dataset.target;
      const container = document.querySelector(targetSelector);
      if (!container) return;

      const amount = 300; // px
      const direction = btn.classList.contains("next") ? 1 : -1;

      container.scrollBy({
        left: direction * amount,
        behavior: "smooth",
      });
    });
  });
});


document.addEventListener("DOMContentLoaded", function () {
  const loadBtn = document.getElementById("load-more-activities");
  const grid = document.getElementById("activity-grid");
  const container = document.getElementById("load-more-container");

  if (loadBtn && grid && container) {
    loadBtn.addEventListener("click", function () {
      const nextPage = this.dataset.nextPage;
      const urlBase = this.dataset.url;
      if (!nextPage || !urlBase) return;

      this.disabled = true;
      this.textContent = "Yükleniyor...";

      fetch(`${urlBase}?page=${nextPage}`)
        .then((resp) => resp.json())
        .then((data) => {
          if (data.html) {
            const temp = document.createElement("div");
            temp.innerHTML = data.html;
            temp.querySelectorAll(".col").forEach((col) => {
              grid.appendChild(col);
            });
          }

          if (data.has_next) {
            loadBtn.dataset.nextPage = data.next_page;
            loadBtn.disabled = false;
            loadBtn.textContent = "Daha Fazla Yükle";
          } else {
            container.innerHTML =
              '<small class="text-muted">Tüm aktiviteler yüklendi.</small>';
          }
        })
        .catch((err) => {
          console.error("Load more error", err);
          loadBtn.disabled = false;
          loadBtn.textContent = "Tekrar dene";
        });
    });
  }
});


document.addEventListener("click", function (e) {
  // Beğen butonu
  const likeBtn = e.target.closest(".activity-like-btn");
  if (likeBtn) {
    const url = likeBtn.dataset.likeUrl;
    const activityId = likeBtn.dataset.activityId;

    fetch(url, { method: "POST" })
      .then((r) => r.json())
      .then((data) => {
        const countSpan = document.querySelector(
          `.activity-like-count[data-activity-id="${activityId}"]`
        );
        if (countSpan) {
          countSpan.textContent = data.like_count;
        }
        if (data.liked) {
          likeBtn.classList.remove("btn-outline-secondary");
          likeBtn.classList.add("btn-primary");
        } else {
          likeBtn.classList.add("btn-outline-secondary");
          likeBtn.classList.remove("btn-primary");
        }
      })
      .catch((err) => console.error("like error", err));
  }

  // Yorum panelini aç/kapat
  const toggle = e.target.closest(".activity-comment-toggle");
  if (toggle) {
    const activityId = toggle.dataset.activityId;
    const box = document.getElementById("activity-comments-" + activityId);
    if (box) {
      box.classList.toggle("d-none");
    }
  }
});

// Yorum formu submit
document.addEventListener("submit", function (e) {
  if (e.target.matches(".comment-form")) {
    e.preventDefault();
    const form = e.target;
    const url = form.dataset.commentUrl;
    const activityId = form.dataset.activityId;
    const formData = new FormData(form);

    fetch(url, {
      method: "POST",
      body: formData,
    })
      .then((r) => r.json())
      .then((data) => {
        if (!data.ok) {
          alert(data.error || "Yorum kaydedilemedi.");
          return;
        }
        const listContainer = document.querySelector(
          `#activity-comments-${activityId} .comment-list`
        );
        if (listContainer) {
          listContainer.innerHTML = data.html;
        }
        const countSpan = document.querySelector(
          `.activity-comment-count[data-activity-id="${activityId}"]`
        );
        if (countSpan) {
          countSpan.textContent = data.comment_count;
        }
        form.reset();
      })
      .catch((err) => console.error("comment error", err));
  }
});
