import matplotlib.pyplot as plt
import numpy as np
import pytest

# Assuming uplt is available in the ultraplot package
from ultraplot import subplots as uplt_subplots


@pytest.fixture(autouse=True)
def close_plots():
    yield
    plt.close('all')

def test_legend_hides_yticklabels_with_sharey_labs_external_legend():
    "Verifies that an external legend (loc='r') causes y-axis tick labels to become hidden when sharey='labs' and last axis is hidden."
    fig, axs = uplt_subplots(ncols=3, sharey='labs')
    
    # Hide the last axis as per the issue
    axs[-1].set_visible(False)
    
    # Plot lines on the visible axes
    for i, ax in enumerate(axs[:-1]):
        ax.plot([0, 1], [i, i + 1], label=f'line {i}')
    
    # Add an external legend to the second-to-last axis
    axs[-2].legend(loc='r')
    
    # Crucial step: draw the canvas to trigger the layout engine where labels are hidden
    fig.canvas.draw()

    # Get the y-axis tick labels for the second-to-last axis
    # The issue states these become hidden. We assert they should be visible for the test to FAIL initially.
    yticklabels = axs[-2].get_yticklabels(minor=False)
    
    # Assert that all major y-tick labels are visible.
    # This assertion should FAIL on the unfixed code if the labels are indeed hidden (visible=False)
    assert all(label.get_visible() for label in yticklabels), "Major y-axis tick labels should be visible (FAILURE EXPECTED)."
    # Although the issue primarily focuses on visibility, it's good practice to ensure text isn't inadvertently cleared.
    assert all(label.get_text() for label in yticklabels), "Major y-axis tick labels should not be empty."

def test_legend_does_not_hide_yticklabels_with_sharey_labs_internal_legend():
    "Confirms that an internal legend (loc='lr') does not hide y-axis tick labels under the same conditions."
    fig, axs = uplt_subplots(ncols=3, sharey='labs')
    
    # Hide the last axis as per the issue
    axs[-1].set_visible(False)
    
    # Plot lines on the visible axes
    for i, ax in enumerate(axs[:-1]):
        ax.plot([0, 1], [i, i + 1], label=f'line {i}')
    
    # Add an internal legend to the second-to-last axis (expected to work)
    axs[-2].legend(loc='lr')
    
    # Crucial step: draw the canvas
    fig.canvas.draw()

    yticklabels = axs[-2].get_yticklabels(minor=False)
    
    # Assert that all major y-tick labels are visible and have text
    # This assertion should PASS.
    assert all(label.get_visible() for label in yticklabels), "Major y-axis tick labels should be visible with internal legend."
    assert all(label.get_text() for label in yticklabels), "Major y-axis tick labels should not be empty with internal legend."

def test_legend_hides_yticklabels_with_sharey_labs_larger_grid():
    "Tests the issue with a larger grid (e.g., 4x4) where the last axis is hidden and an external legend is added."
    fig, axs = uplt_subplots(ncols=4, sharey='labs')
    
    # Hide the last axis
    axs[-1].set_visible(False)
    
    # Plot lines on the visible axes
    for i, ax in enumerate(axs[:-1]):
        ax.plot([0, 1], [i, i + 1], label=f'line {i}')
    
    # Add an external legend to the second-to-last axis
    axs[-2].legend(loc='r')
    
    # Crucial step: draw the canvas
    fig.canvas.draw()

    yticklabels = axs[-2].get_yticklabels(minor=False)
    
    # Assert that all major y-tick labels are visible.
    # This assertion should FAIL on the unfixed code.
    assert all(label.get_visible() for label in yticklabels), "Major y-axis tick labels should be visible in larger grid (FAILURE EXPECTED)."
    assert all(label.get_text() for label in yticklabels), "Major y-axis tick labels should not be empty in larger grid."
