document.addEventListener("DOMContentLoaded", function () {
  const wallList = document.getElementById("wall-list");
  const wallForm = document.getElementById("wall-form");
  let offset = wallList.children.length;
  let loading = false;
  let noMorePosts = false;

  function createPostCard(post) {
    const card = document.createElement("div");
    card.className = "wall-post";
    card.dataset.id = post.id;
    card.innerHTML =
      '<p class="wall-message"></p>' +
      '<div class="wall-meta">' +
      '<span class="wall-author"></span>' +
      '<button class="pray-button"><span>🙏</span> <span class="prayer-count"></span></button>' +
      '</div>';
    card.querySelector(".wall-message").textContent = post.message;
    card.querySelector(".wall-author").textContent = post.author_name || "Anonymous";
    card.querySelector(".prayer-count").textContent = post.prayer_count;
    card.querySelector(".pray-button").dataset.id = post.id;
    return card;
  }

  function loadMorePosts() {
    if (loading || noMorePosts) return;
    loading = true;
    fetch("/api/wall-feed?offset=" + offset)
      .then(res => res.json())
      .then(posts => {
        if (posts.length === 0) { noMorePosts = true; return; }
        posts.forEach(post => wallList.appendChild(createPostCard(post)));
        offset += posts.length;
      })
      .finally(() => { loading = false; });
  }

  window.addEventListener("scroll", function () {
    const nearBottom = window.innerHeight + window.scrollY >= document.body.offsetHeight - 300;
    if (nearBottom) loadMorePosts();
  });

  wallList.addEventListener("click", function (e) {
    const button = e.target.closest(".pray-button");
    if (!button) return;
    button.disabled = true;
    fetch("/api/wall/" + button.dataset.id + "/pray", { method: "POST" })
      .then(res => res.json())
      .then(() => {
        const countSpan = button.querySelector(".prayer-count");
        countSpan.textContent = parseInt(countSpan.textContent) + 1;
      })
      .finally(() => { button.disabled = false; });
  });

  wallForm.addEventListener("submit", function (e) {
    e.preventDefault();
    const message = wallForm.message.value.trim();
    const authorName = wallForm.author_name.value.trim();
    if (!message) return;

    fetch("/api/wall/new", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: message, author_name: authorName })
    })
      .then(res => res.json())
      .then(post => {
        wallList.insertBefore(createPostCard(post), wallList.firstChild);
        offset += 1;
        wallForm.reset();
      });
  });
});
