/* =========================================================
   BIRTHDAY BALLOONS — floats gently in the background of the
   celebrate page for about 30 seconds, then stops.
   =========================================================
   How it works, step by step:

   1. We create one full-screen invisible container (just like
      confetti.js does) to hold every balloon.
   2. Every ~1.6 seconds we spawn ONE new balloon at a random
      spot along the bottom of the screen.
   3. Each balloon gets a random size, color, sideways "sway",
      and rise speed — that's what makes them feel alive
      instead of robotic copies of each other.
   4. CSS (injected below, same trick as confetti.js) handles
      the actual floating-up + swaying animation.
   5. Each balloon removes itself once its own float finishes,
      and after 30 seconds we stop spawning new ones entirely,
      so this doesn't run forever in the background.

   No external library needed — plain "vanilla" JS, same as
   confetti.js.
   ========================================================= */

function floatBirthdayBalloons() {
  // Respect the person's system-level "reduce motion" setting —
  // if it's on, skip balloons entirely rather than create them
  // and immediately hide them.
  const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;
  if (prefersReducedMotion) return;

  const colors = ["#85940c", "#d1d44f", "#8b3a2f", "#e2792a", "#ffd166"];
  const balloonCount = 7; // how many go up in the very first wave

  // Container for every balloon. position: fixed + pointer-events: none
  // means it always covers the screen but never blocks taps/clicks
  // on the card underneath it. z-index: 1 keeps it BEHIND the
  // celebrate card, which is set to z-index: 2 in style.css.
  const container = document.createElement("div");
  container.style.position = "fixed";
  container.style.top = "0";
  container.style.left = "0";
  container.style.width = "100%";
  container.style.height = "100%";
  container.style.pointerEvents = "none";
  container.style.overflow = "hidden";
  container.style.zIndex = "1";
  document.body.prepend(container);

  function spawnBalloon() {
    const balloon = document.createElement("div");
    balloon.className = "birthday-balloon";

    // Randomize each balloon so the sky looks natural, not robotic.
    const size = 34 + Math.random() * 22;        // 34px–56px wide
    const startX = Math.random() * 100;           // 0%–100% across the screen
    const riseDuration = 7 + Math.random() * 5;   // 7s–12s to float to the top
    const sway = 20 + Math.random() * 40;         // how far it drifts sideways
    const color = colors[Math.floor(Math.random() * colors.length)];

    balloon.style.width = size + "px";
    balloon.style.height = size * 1.2 + "px"; // balloons are a bit taller than wide
    balloon.style.background = color;
    balloon.style.left = startX + "%";
    balloon.style.setProperty("--sway", sway + "px");
    balloon.style.animation = `balloon-rise ${riseDuration}s ease-in forwards`;

    container.appendChild(balloon);

    // Clean up this one balloon once it's finished floating up,
    // so old balloons don't quietly pile up in the page's memory.
    setTimeout(() => balloon.remove(), riseDuration * 1000 + 200);
  }

  // Send up the first wave with a slight stagger between each one...
  for (let i = 0; i < balloonCount; i++) {
    setTimeout(spawnBalloon, i * 900);
  }

  // ...then keep sending one new balloon every 1.6 seconds.
  const interval = setInterval(spawnBalloon, 1600);

  // Stop spawning new balloons after 30 seconds. Existing ones on
  // screen still finish their own float — this just stops new ones
  // from starting, so the page settles down instead of running the
  // animation loop forever in the background.
  setTimeout(() => clearInterval(interval), 30000);
}

// Inject the balloon shape + float animation once, the first time
// this file runs (same pattern as confetti.js).
const balloonStyle = document.createElement("style");
balloonStyle.textContent = `
  .birthday-balloon {
    position: absolute;
    bottom: -120px;
    border-radius: 50% 50% 50% 50% / 60% 60% 40% 40%;
    opacity: 0.75;
    filter: drop-shadow(0 2px 3px rgba(0,0,0,0.15));
  }
  /* The thin string hanging below each balloon */
  .birthday-balloon::after {
    content: "";
    position: absolute;
    left: 50%;
    bottom: -22px;
    width: 1px;
    height: 22px;
    background: rgba(0,0,0,0.25);
    transform: translateX(-50%);
  }
  @keyframes balloon-rise {
    0%   { transform: translate(0, 0);              opacity: 0;    }
    10%  {                                          opacity: 0.75; }
    50%  { transform: translate(var(--sway), -55vh);                }
    90%  {                                          opacity: 0.75; }
    100% { transform: translate(0, -115vh);          opacity: 0;    }
  }
`;
document.head.appendChild(balloonStyle);

/* =========================================================
   PHOTO BURST — makes the birthday photo itself feel special:
   soft rings pulse outward from it forever, and a one-time
   ring of sparkles fires outward like a small firework when
   the page first opens.
   =========================================================
   Same idea as the balloons above: no changes needed in
   celebrate.html. This code finds the existing <img> tag on
   the page and wraps it with a new <div> itself, entirely
   from JavaScript, then adds the ring/sparkle elements around
   that wrapper.
   ========================================================= */

function burstPhoto() {
  const img = document.querySelector(".celebrate-card img");
  if (!img) return; // this member has no photo — nothing to animate

  // Wrap the photo in a container so the rings/sparkles have
  // something to sit behind and around it.
  const wrap = document.createElement("div");
  wrap.className = "photo-burst-wrap";
  img.parentNode.insertBefore(wrap, img);
  wrap.appendChild(img);

  // Reduced-motion users still get the wrapper (needed for sizing/
  // layout) but skip the moving rings and firework sparkles —
  // the CSS above also hides them as a second safety net.
  const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;
  if (prefersReducedMotion) return;

  // Two rings, started at different times, so as one fades out
  // the next is already expanding — keeps a gentle pulse going.
  for (let i = 0; i < 2; i++) {
    const ring = document.createElement("div");
    ring.className = "photo-burst-ring";
    ring.style.animationDelay = `${i * 1.2}s`;
    wrap.appendChild(ring);
  }

  // A one-time ring of sparkles shooting outward from the center,
  // like a small firework going off right as the page opens.
  const colors = ["#85940c", "#d1d44f", "#8b3a2f", "#e2792a", "#ffd166"];
  const sparkleCount = 14;

  for (let i = 0; i < sparkleCount; i++) {
    // Spread sparkles evenly in a full circle around the photo.
    const angle = (360 / sparkleCount) * i;
    const distance = 70 + Math.random() * 30; // how far each one travels

    const sparkle = document.createElement("div");
    sparkle.className = "photo-sparkle";
    sparkle.style.background = colors[Math.floor(Math.random() * colors.length)];
    sparkle.style.setProperty("--angle", `${angle}deg`);
    sparkle.style.setProperty("--distance", `${distance}px`);
    sparkle.style.animationDelay = "0.5s"; // fires just after the photo pops in
    wrap.appendChild(sparkle);

    // Clean it up once its own burst animation is done.
    setTimeout(() => sparkle.remove(), 1600);
  }
}

// Start floating balloons and the photo burst as soon as the page loads.
document.addEventListener("DOMContentLoaded", floatBirthdayBalloons);
document.addEventListener("DOMContentLoaded", burstPhoto);
