/*
SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
*/
const STORAGE_KEY = "linumert.operatorLanguage";

export function bindLanguage(doc) {
  const selector = doc.getElementById("operatorLanguage");
  // Only marked labels switch language. Text nodes preserve icons, hints and live values.
  const labels = [...doc.querySelectorAll("[data-en]")].map((element) => ({
    element, text: element.firstChild, pl: element.firstChild.data,
  }));
  let language = "pl";

  function apply(value) {
    language = value === "en" ? "en" : "pl";
    selector.value = language;
    for (const { element, text, pl } of labels) {
      text.data = language === "en" ? element.dataset.en : pl;
      element.lang = language;
    }
  }

  try {
    apply(doc.defaultView.localStorage.getItem(STORAGE_KEY));
  } catch {
    apply("pl");
  }
  selector.addEventListener("change", () => {
    apply(selector.value);
    try {
      doc.defaultView.localStorage.setItem(STORAGE_KEY, language);
    } catch {
      // The active page still switches with storage disabled.
    }
  });
  return { text: (pl, en) => language === "en" ? en : pl };
}
