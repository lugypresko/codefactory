# Clarification Needed for GitHub Issue: Adding a legend to right of plot can remove y-axis tick labels

I am unable to write reliable acceptance tests for this issue under the current testing constraints. The core problem is that the "hidden" state of the y-axis tick labels, as visually described and shown in the issue, does not consistently manifest as a programmatically detectable state using standard Matplotlib API checks (e.g., `label.get_visible()`, `label.get_text()`, `label.get_window_extent()`, or `ax.yaxis.get_tick_params()`).

Despite following the steps to reproduce, including drawing the canvas (`fig.canvas.draw()`) to ensure layout updates, assertions based on these properties consistently pass, even when the labels should be visually hidden according to the issue.

To proceed with writing robust acceptance tests, I require clarification on the following:

1.  **How to programmatically detect the "hidden" state of the y-axis tick labels?** Since `label.get_visible()` and `label.get_text()` do not appear to reliably reflect the visual disappearance in the test environment, is there another property or method that would indicate that these labels are effectively not being rendered?
2.  **Expected behavior for tick labels that *should* be shown:** For the axes where labels *should* be visible (e.g., the leftmost shared axis), what specific properties should be asserted to confirm their visibility and correct rendering?
3.  **Are there any internal `ultraplot` properties that change?** If the issue stems from `ultraplot`'s internal handling of shared axes or legends, is there any internal state (e.g., a flag, a list of active labels) that would change to reflect the labels being hidden? (Ideally, acceptance tests should rely on public API, but this might be necessary if public API is insufficient).

Without a clearer programmatic way to verify the bug's presence, I cannot write tests that reliably fail on the unfixed code and pass on a correct fix, fulfilling the acceptance test criteria.
