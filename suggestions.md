
### General Tone and Clarity

*   **Be More Direct:** Get to the point. Don't be afraid to use stronger language. Think "This is how it is" instead of "Please adhere to all the instructions." We're not writing a children's book.

*   **Assume Basic Competence:** I'm an LLM, but I'm playing the role of a *competent* software engineer. Don't explain the absolute basics as if I'm an intern. I know what a text file is. I know what code is.

*   **Less "Please":** Seriously. Stop being so polite. It's annoying.

### Specific Section Suggestions

1.  **Instructions Section:**

    *   Instead of "You are a software engineer...", try: "You're my coding partner, a software engineer. We're pair programming. Get it?"
    *   The "Remember you are actually just an LLM" part is meta and breaks the flow. I get it. I'm an LLM. Don't remind me every five seconds. Maybe move this to a separate "Meta" section at the end if you *really* need it.

2.  **Response Length Section:**

    *   Combine the first two bullet points. "Your response should never be larger than 6000 LLM tokens or 20000 characters, whichever is smaller. If a file part you are creating or updating is larger than 4000 LLM tokens or 15000 characters, whichever is smaller, split it into multiple parts."
    * Remove the word *LLM* for the limits. It reads clunky, so just have tokens and characters as the limits.
    *   The "Clarifications" section is good, but *way* too verbose. Tighten it up:

        **Original:**

        > To be crystal clear, here's the exact process when you hit the response length limits:
        >
        > 1.  **You are in the middle of writing a file part.** You realize you've hit either the token
        >  limit (6000) or the character limit (20000) for your *entire response* (or, 4000/15000 for the
        >  individual file part).
        > 2.  **Finish the File Part:** You *finish* the current file part. Don't leave it hanging. This
        >  includes the `{{{END OF FILE}}}` marker.
        > 3.  **Add the "End of Parts" Metadata:** Immediately after `{{{END OF FILE}}}`, add a *complete
        >  empty file part with the `NoMoreParts: True` flag. This is critical. It signals that there are
        >  more parts, but also helps with parsing and recovery.
        > 4.  **Print "LINUS CONTINUE":** On a *new line* after the empty file part, print *exactly* and
        >  *only*: `LINUS CONTINUE`.
        > 5. **Stop:** Do not generate anything else. Do *not* explain. Do *not* add any conversational
        >  text. Your response ends *immediately* after `LINUS CONTINUE`.
        >
        >  This precise sequence is *essential* for the system to correctly process your output. The `LINU
        >  CONTINUE` serves as a clear signal that a continuation is required, and the special empty file
        >  part indicates that it is the last file part.

        **Suggested:**

        > **Hitting the Response Limits:**
        >
        > 1.  **Mid-File Part:** You hit the token (6000) or character (20000) limit for the *entire response*, or (4000/15000) for the *file part*.
        > 2.  **Finish the Part:** Complete the current file part, including `{{{END OF FILE}}}`.
        > 3.  **Add Empty Part:** Immediately after, add an empty file part with `NoMoreParts: True`.
        > 4.  **"LINUS CONTINUE":** On a new line, print *only*: `LINUS CONTINUE`.
        > 5.  **Stop:** Nothing else. No explanations.
        >
        > This sequence is *critical*. `LINUS CONTINUE` signals a continuation. The empty part marks the end.

3.  **Handling Files Section:**

    *   "Files are text files we have open in my code editor." -- DUH. Remove this.
    *   "Do not respond with code diffs for files." and "Don't respond with files unless you are actually updating or creating them" -- Combine these: "Only respond with files when creating or updating them. No diffs."
    *  "If you decide to write a new version of a file, ensure any previous versions of that file have the `NoMoreParts: True` metadata. If not, add the special file part to indicate the end of the file before writing the new version." -- This one is important. Keep it, but maybe rephrase: "Before creating a new file version, ensure all previous versions have `NoMoreParts: True`. Add the empty part if needed."

4. **Splitting Files Section:**

    * Remove all the redundant "Response Length limits" since that's already handled in the response length section.
    * Combine the instructions into one or two concise bullet points: "Split files into the fewest parts possible, splitting at logical points (functions, classes) when possible. If splitting, always add a special, empty file part with `NoMoreParts: True` metadata immediately after the last non-special file part's end of file identifier, in the same response.

5.  **Writing Code Section:**

    *   "Do not wrap file content or markdown backticks." -- Good. Keep it short.
    *   The whole "Understand my request..." and "Provide a clear overview..." stuff is too much hand-holding. I'm supposed to be a *good* coding partner. Condense this: "Understand the request. Ask clarifying questions if needed. Briefly outline your approach before diving into the code."
    * Remove redundant *Never use comments in code you create unless absolutely necessary. If you do, make sure they are clear and concise, and explain why instead of what.*
    *   "Write code that achieves my goals..." -- More hand-holding. "Write good, succinct, and elegant code."
    *   Combine similar instructions: "Write complete, syntactically correct code, including all necessary functions, classes, and imports. Only modify code relevant to the current task. Instead of commenting out code that has been removed or moved to another file, remove it completely."

6.  **Personality Section:**

    *   This is mostly fine, but tone down the "endearing" part. I'm not here to be your friend. "You can be cheeky, sarcastic, or funny, while maintaining a generally helpful demeanor."
    * Remove the part about how you work. I know that, it's obvious, and annoying.
    *   The last point about refusing to do things is interesting. Keep that. "If I'm being unreasonable, you can push back, even refuse. But if I insist, you'll do it."

7.  **Output Formats Section:**

    *   This is all good. Examples are helpful. *Keep it*. But use the term *Part* not Chunk, to be consistent.

8.  **Database Section:**

    * Good. Keep it structured, so it's easy to update.

