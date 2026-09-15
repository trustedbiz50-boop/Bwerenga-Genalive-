/* =========================================================
   CONFETTI BURST — plays once when the success page loads.
   =========================================================
   How it works, step by step:

   1. We create a bunch of small <div> "confetti pieces" and
      drop them into a container on the page.
   2. Each piece gets a random horizontal starting position,
      a random color from our brand palette, a random size,
      a random rotation, and a random fall speed.
   3. CSS (see the <style> block this file injects) handles the
      actual falling + spinning animation — JS just sets the
      random starting values so every piece looks different.
   4. After the animation finishes, we remove the pieces from
      the page so they don't sit around uselessly in memory.

   No external library needed — this is plain "vanilla" JS.
   ========================================================= */

function burstConfetti() {
  const colors = ["#85940c", "#d1d44f", "#8b3a2f", "#e2792a", "#ffd166"];
  const pieceCount = 90;

  // Container that holds all the confetti pieces.
  // position: fixed + covers the whole screen, but pointer-events: none
  // so it never blocks clicks on the page underneath it.
  const container = document.createElement("div");
  container.style.position = "fixed";
  container.style.top = "0";
  container.style.left = "0";
  container.style.width = "100%";
  container.style.height = "100%";
  container.style.pointerEvents = "none";
  container.style.overflow = "hidden";
  container.style.zIndex = "9999";
  document.body.appendChild(container);

  for (let i = 0; i < pieceCount; i++) {
    const piece = document.createElement("div");
    piece.className = "confetti-piece";

    // Randomize each piece so the burst looks natural, not robotic.
    const size = 6 + Math.random() * 8;            // 6px–14px
    const startX = Math.random() * 100;              // 0%–100% of screen width
    const fallDuration = 2.5 + Math.random() * 1.5;   // 2.5s–4s
    const delay = Math.random() * 0.3;                // slight stagger
    const rotateStart = Math.random() * 360;
    const drift = (Math.random() - 0.5) * 200;        // sideways drift in px
    const color = colors[Math.floor(Math.random() * colors.length)];

    piece.style.width = size + "px";
    piece.style.height = size * 0.4 + "px"; // rectangles look more like paper than circles
    piece.style.background = color;
    piece.style.left = startX + "%";
    piece.style.top = "-20px";
    piece.style.transform = `rotate(${rotateStart}deg)`;
    piece.style.animation = `confetti-fall ${fallDuration}s ease-in ${delay}s forwards`;
    piece.style.setProperty("--drift", drift + "px");

    container.appendChild(piece);
  }

  // Clean up after the longest possible piece has finished falling.
  setTimeout(() => {
    container.remove();
  }, 4200);
}

// Inject the keyframe animation once, the first time this file runs.
const style = document.createElement("style");
style.textContent = `
  .confetti-piece {
    position: absolute;
    opacity: 0.95;
    border-radius: 1px;
  }
  @keyframes confetti-fall {
    0% {
      transform: translate(0, 0) rotate(0deg);
      opacity: 1;
    }
    100% {
      transform: translate(var(--drift), 105vh) rotate(600deg);
      opacity: 0.9;
    }
  }
`;
document.head.appendChild(style);

// Fire the burst as soon as this page finishes loading.
document.addEventListener("DOMContentLoaded", burstConfetti);
