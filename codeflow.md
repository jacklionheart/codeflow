# Codeflow Ignore

## Goal
Add support for a ".codeflowignore" file that works just like a git ignore file.
We also should change the way we do ignore rules to build up over time as we recurse from the project_dir into specific files. At each dir starting from project_dir we should check
for both .codeflowignore and .gitignore files and concatenate the contents in a way that makes sense -- when we something like /blah, we need to not respect that at later levels, but for blah we do (if i remember my git ignore).

The requirement is that each .gitignore/.codeflow file is respected exactly as it would be by git. Please spell out what those expectations are and write tests for them.
We should warn on paths that are somehow "broken", but not fail.
We'll want additional test to see that .codeflow and .gitignore are both being picked up correctly.

Questions:
> * If we have `/foo/*.py` in a parent directory's .codeflowignore, but `/foo/important.py` in a child directory's .codeflowignore, which should win?

There shouldnt be any conflict. If any gitignore file anywhere in your ancestry says you're excluded, you're excluded. The only logical complexity is applying each pattern at the right level of the hierarchy. We might need to do more "pre-filtering" of whole subtrees, too and rely on that in order to make the logic simple and elegant.
Compatability doesn't need to be 100%, but it should work for most real life use cases. Here's one example that needs to work:

*.pyc
__pycache__
/wandb
train_dir
replays
*.egg-info
/build/
/build_debug/
.DS_Store
.task
outputs
*.so
cython_debug
stats.profile
/dist
player/dist
player/node_modules


Please write one test that uses this specific test builds a complex environment and filters on it against a slightly simplified version of this file. You can repeat any line that wouldnt really involve "new" logic, but maintain the full coverage.

## Output
codeflow/io/file.py
tests/io/test_file.py


## Questions

### maya's questions
To effectively support a ".codeflowignore" file and refine the implementation of ignore rules, it's crucial to establish a thorough understanding of the project requirements. Here are some illustrative questions to clarify the goals and align efforts:

### 1. Understanding Functional Requirements
- **Define the Parsing Logic:** How should the ignore rules be parsed and interpreted, especially when combining rules from both ".codeflowignore" and ".gitignore" files? What specific patterns and exceptions need to be handled (e.g., negations, directory-specific rules, pattern precedence)?
- **Scope of Ignore Application:** Should ignored patterns apply only to directories and files at their respective levels, or should some rules persist through the directory hierarchy? In cases where patterns conflict, what logic determines which rule takes precedence?
- **Impact on Existing Functionality:** How will this new feature integrate with existing project functionalities? Are there specific components or systems within the project where introducing this feature could cause conflicts or require revisions?

### 2. Performance and Scalability
- **Efficiency of Rule Evaluation:** How should the implementation optimize the evaluation of ignore rules, especially in large directories with numerous nested folders and files? What mechanisms should be employed to ensure that checking for ignores does not significantly impact file processing performance?
- **Handling Large .codeflowignore Files:** What strategies will be used to handle potentially large ".codeflowignore" files efficiently? Are there any limits on the size or complexity of ignore rules that the system should impose to maintain performance?

### 3. User Experience and Usability
- **User Feedback and Error Handling:** How should the system handle invalid or conflicting patterns within ".codeflowignore"? What feedback will users receive if their ignore rules are not applied as expected?
- **Documentation and Support:** What documentation should accompany the ".codeflowignore" feature to assist users in creating and managing their ignore files effectively? Are there specific patterns or use cases that should be highlighted to help users understand how to use the feature?

### 4. Testing and Validation
- **Test Coverage:** What types of tests are necessary to ensure the ".codeflowignore" feature works reliably? Should the testing strategy include edge cases like recursive patterns, conflicting rules, and scenarios with both ".codeflowignore" and ".gitignore" interactions?
- **Validation Criteria:** What criteria will be used to validate that the implementation meets its goals? Are there any specific metrics or benchmarks the feature must achieve before it's considered successful?

### 5. Integration with Existing Tools
- **Syncing with Git Functionality:** How will ".codeflowignore" seamlessly work alongside existing ".gitignore" rules? Are there any existing integration points or configurations in Git that might affect the operation of this new feature?
- **Potential Conflicts with Other Tools:** Might there be conflicts with other tools or scripts that operate within the same directories, and what strategies should be in place to address these issues?

Addressing these questions collectively will help guide the project's successful execution, ensure the delivery of a robust ".codeflowignore" feature, and promote clarity in the project's objectives and expectations.

### merlin's questions
Let me ask some clarifying questions to ensure we understand the requirements and implications clearly:

1. Pattern Inheritance & Scope
   * How should patterns from different directory levels combine? 
   * If we have `/foo/*.py` in a parent directory's .codeflowignore, but `/foo/important.py` in a child directory's .codeflowignore, which should win?
   * Should there be any difference in precedence between .gitignore and .codeflowignore patterns at the same directory level?

2. Performance & Caching
   * Do we need to support watching for changes to .codeflowignore/.gitignore files?
   * Should we cache the compiled ignore patterns for each directory to avoid re-parsing?
   * What's the expected scale - how many files/directories might we be dealing with?

3. Compatibility & Testing
   * Do we need 100% compatibility with git's ignore pattern syntax? (Including exotic features like character ranges `[a-z]`, etc)
   * Should we support the `!` negation syntax from git to un-ignore previously ignored paths?
   * What test cases would give us confidence in the implementation - especially around the hierarchical pattern inheritance?

4. Integration Questions
   * Where in the existing codebase is file traversal/filtering happening now?
   * Are there any existing ignore mechanisms we need to maintain compatibility with?
   * Should this be an opt-in feature or enabled by default?

The key challenges seem to be:
1. Correctly implementing the hierarchical pattern inheritance 
2. Ensuring efficient pattern matching at scale
3. Maintaining compatibility with git's ignore syntax
4. Testing the interaction of patterns across directory levels

Would you like me to focus on any particular aspect of these questions first?
