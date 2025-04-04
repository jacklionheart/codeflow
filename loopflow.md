# Loopflow Communication Update

## Goal

Add a command `code-context --profile` that can be used to help with understanding the distribution of token counts within a codebase.
Use `tiktoken` to count the tokens. Just use a simple single config that's "modern" for Claude and ChatGPT. No need to be precise or consider which LLM is actually getting the request. Otherwise, maintain the same arg input structure ad code-context for defining the overall set of code to profile.

For now, print two charts:
* one that is hierarchical. tokens in each subdir: Show total # tokens (including its subdirs), % of tokens its parent, and % of the total.
* one that is by type. for each file type present in the codebase, show total # tokens and % of total tokens. 

All filters to code-context (e.g. the file-type filter) should work here to. if we filter to py files, all of the above should be filtered.


Q&A 
1. **Experimental Value & Hypothesis**
   - What specific hypotheses about code structure and LLM processing are we trying to test with this profiling?
   - Are we primarily interested in identifying "hot spots" of token complexity, or in understanding the overall distribution patterns?
   - How might this inform our choices about code refactoring or chunking strategies for LLM processing?

The main goal here is to make it easier to use loopflow within a large codebase where its not easy to just incldue all the relevant code without hitting context window limits. This will allow users to see what they need to cut out.

2. **Token Counting Methodology**
   - For hierarchical counting, should we count tokens in files like __init__.py that might be duplicated in multiple places?
   - How should we handle symbolic links or duplicated code?
   - Should we have a way to identify "dense" vs "sparse" token regions (e.g. tokens per line or tokens per byte)?

Nothing should be duplicated ever. We're not executing any code. We just go through the directory according to the same logic as exists and instead of copying the output we're adding the data to a token profiling tool. You can base the token profiler of this time profiler I wrote:

"""
profiler.py
Hierarchical performance tracker with context-manager API and automatic nesting.

This module provides a Profiler class that enables tracking execution time across
various parts of your code in a hierarchical manner using relative labels. Key features include:

1. Context-manager API for clean, exception-safe timing
2. Automatic nesting of timers based on execution context
3. Node caching and time accumulation across repeated operations
4. Support for retrieving statistics including percentages of parent/total time,
   call counts, and detailed percentile statistics (min, max, mean, p5, p95, etc.)
5. Low overhead when disabled

Usage example:
    profiler = Profiler(enabled=True)
    with profiler.track("rollout"):
        # time rollout code
        with profiler.track("step"):  # Note: this is relative to "rollout"
            # time environment step call
            with profiler.track("env"):  # Note: this is relative to "rollout/step"
                # time environment operation
                ...
    stats = profiler.get_stats()  # returns a nested dict of timings
"""

import time
import random
from contextlib import contextmanager
from typing import Optional, Dict, List
import numpy as np

class TimingNode:
    def __init__(self, label: str, parent: Optional["TimingNode"] = None, max_samples: int = 100):
        self.label = label              # local label only
        self.parent = parent
        self.previous_total = 0.0       # accumulated time from previous runs
        self.start_time = None          # current start time (None if not running)
        self.children: Dict[str, "TimingNode"] = {}  # keyed by local label
        self.count = 0                  # number of times this node was entered
        self.durations: List[float] = []  # list to store durations of each call
        self.max_samples = max_samples  # maximum number of duration samples to keep

    def start(self):
        if self.start_time is not None:
            raise RuntimeError(f"Timer '{self.label}' is already running.")
        self.start_time = time.perf_counter()
        self.count += 1

    def stop(self) -> float:
        if self.start_time is None:
            raise RuntimeError(f"Timer '{self.label}' was not started!")
        elapsed = time.perf_counter() - self.start_time
        self.previous_total += elapsed
        
        # Add duration using reservoir sampling to maintain max_samples limit
        if len(self.durations) >= self.max_samples:
            idx = random.randint(0, self.count - 1)  # Use count for better distribution
            if idx < self.max_samples:  # Only replace if idx is within our sample array
                self.durations[idx] = elapsed
        else:
            self.durations.append(elapsed)
            
        self.start_time = None
        return elapsed

    def running_total(self) -> float:
        """Return total accumulated time plus running time if still active."""
        if self.start_time is not None:
            return self.previous_total + (time.perf_counter() - self.start_time)
        return self.previous_total

class Profiler:
    """
    Hierarchical profiler with context-manager API, auto nesting, and comprehensive statistics.
    Uses relative labels for simpler usage without a built-in root node.

    Usage example:
        profiler = Profiler(enabled=True)
        with profiler.track("main"):  # Create your own root
            # time main code
            with profiler.track("step"):  # Relative to "main"
                # time step call
                with profiler.track("env"):  # Relative to "main/step"
                    # time environment operation
                    ...
        stats = profiler.get_stats()  # returns a nested dict of timings

    The profiler caches nodes by full path so that repeated uses accumulate times.
    """
    def __init__(self, enabled: bool = True, max_samples: int = 100):
        self.enabled = enabled
        self.max_samples = max_samples
        self.stack = []  # No default root node
        self.node_cache: Dict[str, TimingNode] = {}

    @contextmanager
    def track(self, label: str):
        """
        Use as a context manager to time a code block. The provided label is automatically
        nested under the current active node if one exists. Labels are relative to the current context.
        If the same label is used again in the same position, its time is accumulated.
        """
        if not self.enabled:
            yield
            return

        if not label:
            raise ValueError("Empty label is not allowed")
            
        # Handle the case where this might be a root-level node
        if not self.stack:
            # This is a root level node
            full_label = label
            parent = None
        else:
            # This is a child node, create proper path
            parent = self.stack[-1]
            parent_path = self._get_full_path(parent)
            full_label = f"{parent_path}/{label}" if parent_path else label
        
        # Get or create the node
        if full_label in self.node_cache:
            node = self.node_cache[full_label]
            if node.start_time is not None:
                raise RuntimeError(f"Node '{full_label}' is already running.")
        else:
            node = TimingNode(label, parent, max_samples=self.max_samples)
            self.node_cache[full_label] = node
            if parent:
                parent.children[label] = node
        
        # Start timing and add to stack
        node.start()
        self.stack.append(node)
        
        try:
            yield
        finally:
            # Ensure we're stopping the correct node
            if self.stack and self.stack[-1] == node:
                node.stop()
                self.stack.pop()
            else:
                # This shouldn't happen with proper context manager usage
                raise RuntimeError(f"Profiler stack corruption detected while stopping '{full_label}'")

    def _get_full_path(self, node: TimingNode) -> str:
        """Return the full hierarchical path for a node."""
        if node is None:
            return ""
            
        parts = []
        current = node
        while current.parent is not None:
            parts.append(current.label)
            current = current.parent
        
        # Add the root node's label if it exists
        if current:  # This should be the root node
            parts.append(current.label)
            
        return "/".join(reversed(parts))

    def get_stats(self) -> Dict[str, Dict[str, float]]:
        """
        Returns a dictionary mapping each node's full hierarchical path
        to its timing statistics:
            - total_time: The running total time.
            - pct_of_parent: Percentage of parent's time.
            - pct_of_total: Percentage of overall total time.
            - count: Number of times this node was entered.
            - min: Minimum call duration among samples.
            - max: Maximum call duration among samples.
            - mean: Mean call duration among samples.
            - p5: 5th percentile of call duration.
            - p95: 95th percentile of call duration.
        """
        stats = {}
        
        # Find the total time across all root nodes
        total_time = sum(node.running_total() for node in self.node_cache.values() 
                        if node.parent is None)
        
        # If no timing has been done, return empty stats
        if total_time <= 0:
            return stats
            
        # Process each node in the cache to build stats dictionary
        for full_path, node in self.node_cache.items():
            node_total = node.running_total()
            
            # Calculate parent total time for percentage calculation
            parent_total = 0.0
            if node.parent:
                parent_path = self._get_full_path(node.parent)
                parent_node = self.node_cache.get(parent_path)
                if parent_node:
                    parent_total = parent_node.running_total()
            else:
                # For root nodes, parent total is the overall total
                parent_total = total_time
                
            # Build samples array for statistics
            samples = []
            if node.count > 0:
                # Add stored durations
                if node.durations:
                    samples.extend(node.durations)
                
                # If node is currently running, add current duration
                if node.start_time is not None:
                    current_duration = time.perf_counter() - node.start_time
                    samples.append(current_duration)
                
            # Calculate statistics if we have samples
            if samples:
                samples_array = np.array(samples)
                min_val = float(np.min(samples_array))
                max_val = float(np.max(samples_array))
                mean_val = float(np.mean(samples_array))
                p5 = float(np.percentile(samples_array, 5)) if len(samples) > 1 else min_val
                p95 = float(np.percentile(samples_array, 95)) if len(samples) > 1 else max_val
            else:
                min_val = max_val = mean_val = p5 = p95 = 0.0

            # Calculate percentages
            pct_of_parent = 0.0
            if parent_total > 0:
                pct_of_parent = (node_total / parent_total * 100)
                
            pct_of_total = 0.0
            if total_time > 0:
                pct_of_total = (node_total / total_time * 100)
            
            # Store statistics
            stats[full_path] = {
                "total_time": node_total,
                "pct_of_parent": pct_of_parent,
                "pct_of_total": pct_of_total,
                "count": node.count,
                "min": min_val,
                "max": max_val,
                "mean": mean_val,
                "p5": p5,
                "p95": p95,
            }
            
        return stats
        
    def reset(self):
        """Reset the profiler to its initial state."""
        self.stack = []
        self.node_cache = {}
    

3. **Visualization & Thresholds**
   - Would it be valuable to have configurable thresholds for the hierarchical view (e.g. only show dirs with >5% of total)?
   - Should we highlight directories or file types that exceed certain token density thresholds?
   - Would a visual indicator of token distribution (like ascii charts) be helpful?

We'll explore more complex visualizations later. Good ideas but too early.

4. **Integration with Existing Code-Context**
   - How should this interact with existing filters like --exclude and --include?
   - Should we maintain separate caches for token counts vs regular code context?
   - Should token profiling become part of the standard code-context output or remain a separate mode?

Conceptually, there should be one system that loopflow uses to define a set of files given an input sequence (including --exclude etc). That algorithm should be literally shared (as in exact same code) by the system that goes through it to profile as the one that goes through it to copy the output.

1. **Token Counting Methodology:**
   - What specific configuration of `tiktoken` should be used for counting tokens? Is there a predefined "modern" configuration that should be considered, and what are its characteristics, such as tokenization rules?
   - How should the tool handle files or directories that do not match the specified config or are incompatible with the token counting process?

I don't know. Start simple but make it work. I can change this easily later.

2. **Hierarchical Token Distribution:**
   - Should the hierarchical chart represent token counts visually or through text, and what level of detail is expected (e.g., depth of subdirectories)?
   - How should the analysis handle nested directories with similar names? Should there be an aggregation of token counts at multiple directory levels?

For now let's use all levels of subdirectories.
There shouldnt be any speical logic for similar names.


3. **File Type Token Distribution:**
   - Is there a specific format or visualization preferred for the distribution by file type? Should it support both graphical (like pie charts) and textual outputs, or is a simple text chart sufficient?
   - How should the tool handle atypical file types or extensions that don’t correspond to conventional programming files?

A simple text chart is ok for now. Just make sure the rendering code is isolated from the actual gathering and storing of the profile data.
The took now filters out a lot of code such as binary files. Let's do the same as the existing code-context code.

4. **Filters and Arguments:**
   - How will the current filters and arguments in `code-context` be integrated with the `--profile` command? Should there be a mechanism to extend or adapt the filter functionality specifically for token distribution profiling?
   - Are there any edge cases or specific situations where these filters should behave differently than the existing implementation?

You may need to abstract out some definition of a FileSet or CodebaseSubset or something. But only if necessary.

5. **Performance and Scalability:**
   - Given that tokenization could potentially be resource-intensive, particularly for larger codebases, what performance considerations should be factored in regarding memory usage and processing time?
   - Should there be a provision for running the tool incrementally over a large codebase, perhaps by caching intermediate results or supporting parallel processing?

This should be done efficiently. As long as we're scanning each file one things should be fine. i dont think we need to do any explicit parallelism.

6. **User Experience and Output:**
   - What level of customization should be available for users in terms of specifying the output format (e.g., plain text, JSON, graphs)?
   - Is it important for the output to be compatible with other tools or systems (e.g., CI/CD pipelines), and should there be an option to export results to different formats?

   No customization for now. Make it easy to adapt the code, but not easy to do so via the command line. No integrations with outside visualizations for now.

## Output
loopflow/cli/code_context.py
tests/io/file.py
tests/io/token_profiler.py
loopflow/io/file.py
loopflow/io/token_profiler.py
## Team
merlin
maya


## Reviews

### merlin's review
Let me review the drafts and provide feedback on the key aspects:

### Criteria & Scoring

1. **Architecture & Integration (7/10)**
- Strengths: Clean separation between profiling and rendering, follows existing patterns
- Areas for improvement: Could better abstract the concept of a "FileSet" to share with code-context

2. **Token Counting Implementation (8/10)**
- Strengths: Uses tiktoken effectively, handles hierarchy well
- Areas for improvement: Could add basic validation/error checking around token counts

3. **Code Organization & Maintainability (6/10)** 
- Strengths: Clear class structure, separation of concerns
- Areas for improvement: Some duplication between draft files, needs consolidation

### Draft-Specific Feedback

For `code_context.py`:
- Good: Clear tokenization approach using tiktoken
- Improvement needed: Should leverage existing file filtering logic more explicitly

For `file.py`:
- Good: Comprehensive file handling with appropriate filters
- Could be refactored to share logic with token profiling

For `token_profiler.py`:
- Strong implementation of hierarchical tracking
- Good separation of data collection from presentation
- Could benefit from more explicit error handling

### Key Recommendations

1. **Consolidate File Selection Logic**
```python
class CodebaseSubset:
    """Defines a set of files based on filters and root paths."""
    def __init__(self, root: Path, extensions: Optional[Tuple[str, ...]] = None):
        self.root = root
        self.extensions = extensions
    
    def iter_files(self) -> Iterator[Path]:
        """Iterate through matching files applying filters."""
        # Shared logic from file.py
```

2. **Strengthen Token Counting Validation**
```python
class TokenCounter:
    def __init__(self, encoding: str = "cl100k_base"):
        self.encoder = tiktoken.get_encoding(encoding)
    
    def count_tokens(self, content: str) -> Optional[int]:
        try:
            return len(self.encoder.encode(content))
        except Exception as e:
            logger.warning(f"Token counting failed: {e}")
            return None
```

3. **Cleaner Integration with Existing Code**
```python
def profile_code_context(files: CodebaseSubset) -> str:
    profiler = TokenProfiler()
    for file in files.iter_files():
        profiler.process_file(file)
    return profiler.get_stats()
```

### Summary

The drafts provide a solid foundation but would benefit from:
1. More explicit sharing of file selection logic with code-context
2. Better error handling and validation in token counting
3. Clearer integration points with the existing codebase

The core tokenization and hierarchical tracking approaches are sound. The main area for improvement is in better integrating with and leveraging the existing code-context infrastructure.

I recommend focusing next iteration on:
1. Extracting shared file selection logic into a reusable component 
2. Adding proper error handling and validation
3. Cleaning up the integration points between components

Let me know if you would like me to expand on any of these points or provide more specific code examples.

### maya's review
# Review of Implementation Proposal

## Overview
The proposed implementation introduces a `code-context --profile` command with the goal of analyzing and understanding the distribution of token counts in a codebase. Leveraging `tiktoken` for token counting, the system will provide insights into token distribution both hierarchically by directory and by file type. The primary focus is on enabling users to identify areas of high token density which can be crucial for efforts such as optimizing code for LLMs' context limits.

### Review and Evaluation Criteria

#### 1. **Integration with Existing Code-Context Functionality (Score: 7)**
- **Relevance**: The proposal integrates the new profiling functionality with the current code-context system, leveraging existing filtering logic.
- **Observations**: The system should ideally share the codebase traversal logic between output generation and profiling to ensure consistency and avoid redundancy.
- **Recommendations**: Strengthen and test the integration points to ensure that all filters (e.g., `--exclude`, `--include`) function seamlessly with the profiling feature. This may require abstracting file-processing logic into common modules.

#### 2. **Token Counting Methodology (Score: 8)**
- **Relevance**: The utilization of `tiktoken` with a baseline modern encoding for token counting is a key component.
- **Observations**: The approach uses a consistent method for token counting across all file assessments, but the encoding configuration remains relatively basic.
- **Recommendations**: Clarify what "modern" configuration needs entail. Consider potential future scenarios where dynamic encoding adjustments might be necessary, while starting with your chosen 'cl100k_base' as a solid baseline.

#### 3. **Hierarchical and File Type Analysis (Score: 8)**
- **Relevance**: Providing hierarchical and file-type token distribution analytics is central to the proposal's objectives.
- **Observations**: The token distribution is computed effectively, and reports are formatted clearly using concise structuring that separates hierarchy and file type.
- **Recommendations**: Consider potential enhancements like filtering or thresholding for more granular control in future iterations. Provide configurable output options once the core functionality is stable.

#### 4. **Performance Considerations (Score: 7)**
- **Relevance**: Performance is vital due to the potential scale of codebases analyzed.
- **Observations**: While designed for efficiency by avoiding duplication and leveraging file-based contexts, explicit parallelism or optimizations are not explored.
- **Recommendations**: Investigate performance optimizations after the core functionalities are stable, possibly using parallel file processing or caching repeated analyses to enhance throughput.

#### 5. **Error Handling and Robustness (Score: 7)**
- **Relevance**: Robust error handling ensures that the profiling doesn't fail unexpectedly.
- **Observations**: Basic error handling has been added, but there is room to improve by logging more granular diagnostics.
- **Recommendations**: Incorporate enhanced error handling, including logging errors and processing anomalies during profiling, potentially returning partial results with flagged issues.

### Overall Summary
The draft thoroughly addresses the requirements for integrating token profiling into the `code-context` system, effectively utilizing tokenization tools to deliver meaningful insights about token distribution. The modular design is evident from the separation of data gathering and representation. Areas for further development include refining integration with existing filters, enhancing configurability for user-specific preferences, and exploring optimizations for dealing with large-scale codebases. Emphasizing robust error handling and clear diagnostic reporting will also increase the system's resilience and usability.

The next iteration could prioritizing expanding upon integration tests, building configurable output targets, refining performance optimizations, and enhancing error diagnostics to ensure a comprehensive, user-centric expansion of the `code-context` capabilities.
