// Small progressive enhancements. The app works without JavaScript.
document.addEventListener("DOMContentLoaded", () => {
  // Interview rounds: add / remove rows on the application form
  const rounds = document.getElementById("rounds");
  const template = document.getElementById("round-template");
  document.querySelectorAll("[data-add-round]").forEach((btn) =>
    btn.addEventListener("click", () => {
      rounds.appendChild(template.content.cloneNode(true));
      rounds.lastElementChild.querySelector("input").focus();
    })
  );
  document.addEventListener("click", (e) => {
    const remove = e.target.closest("[data-remove-round]");
    if (!remove) return;
    const row = remove.closest(".round-row");
    if (rounds.children.length > 1) row.remove();
    else row.querySelectorAll("input").forEach((i) => (i.value = ""));
  });

  // Live chip preview for the job requirements field
  document.querySelectorAll("[data-chip-preview]").forEach((input) => {
    const target = document.getElementById(input.dataset.chipPreview);
    const render = () => {
      const seen = new Set();
      target.innerHTML = "";
      input.value.split(",").map((s) => s.trim()).filter(Boolean).forEach((s) => {
        if (seen.has(s.toLowerCase())) return;
        seen.add(s.toLowerCase());
        const chip = document.createElement("span");
        chip.className = "chip";
        chip.textContent = s;
        target.appendChild(chip);
      });
    };
    input.addEventListener("input", render);
    render();
  });

  // Job Match: click a suggested skill to add/remove it from the input
  const skillsInput = document.getElementById("skills");
  document.querySelectorAll("[data-skill]").forEach((btn) =>
    btn.addEventListener("click", () => {
      const skill = btn.dataset.skill;
      let list = skillsInput.value.split(",").map((s) => s.trim()).filter(Boolean);
      const has = list.some((s) => s.toLowerCase() === skill.toLowerCase());
      list = has ? list.filter((s) => s.toLowerCase() !== skill.toLowerCase()) : [...list, skill];
      skillsInput.value = list.join(", ");
      btn.classList.toggle("on", !has);
    })
  );
});
