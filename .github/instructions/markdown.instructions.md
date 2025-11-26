---
description: 'Documentation and content creation standards'
applyTo: '**/*.md'
---

## General Guidelines
- Write clear and concise documentation.
- Use consistent terminology and style.
- Ensure accuracy and completeness of information.
- Avoid jargon and technical terms unless necessary; explain them if used.
- Use clear, unambiguous language.

## Grammar
* Use present tense verbs (is, open) instead of past tense (was, opened).
* Write factual statements and direct commands. Avoid hypotheticals like "could" or "would".
* Use active voice where the subject performs the action.
* Write in second person (you) to speak directly to readers.

## Markdown Content Rules

The following markdown content rules are enforced in the validators:

1. **Headings**: Use appropriate heading levels (H2, H3, etc.) to structure your content. Do not use an H1 heading, as this will be generated based on the title.
2. **Lists**: Use bullet points or numbered lists for lists. Ensure proper indentation and spacing.
3. **Code Blocks**: Use fenced code blocks for code snippets. Specify the language for syntax highlighting.
4. **Links**: Use proper markdown syntax for links. Ensure that links are valid and accessible.
5. **Images**: Use proper markdown syntax for images. Include alt text for accessibility.
6. **Tables**: Use markdown tables for tabular data. Ensure proper formatting and alignment.
7. **Line Length**: Keep prose to roughly 140 characters per line for readability; README-style docs can stretch to 250–300 characters when long URLs or commands make wrapping awkward.
8. **Whitespace**: Use appropriate whitespace to separate sections and improve readability.
9. **Front Matter**: Include YAML front matter at the beginning of the file with required metadata fields.

## Formatting and Structure

Follow these guidelines for formatting and structuring your markdown content:

- **Headings**: Use `##` for H2 and `###` for H3. Ensure that headings are used in a hierarchical manner. Recommend restructuring if content includes H4, and more strongly recommend for H5.
- **Lists**: Use `-` for bullet points and `1.` for numbered lists. Indent nested lists with two spaces.
- **Code Blocks**: Use triple backticks (`) to create fenced code blocks. Specify the language after the opening backticks for syntax highlighting (e.g., `csharp).
- **Links**: Use `[link text](https://example.com)` for links. Ensure that the link text is descriptive and the URL is valid.
- **Images**: Use `![alt text](https://example.com/image.png)` for images. Include a brief description of the image in the alt text.
- **Tables**: Use `|` to create tables. Ensure that columns are properly aligned and headers are included.
- **Line Length**: Aim for ~140 characters per line in most docs. README or release notes can extend to ~250–300 characters when necessary; beyond that, prefer soft breaks.
- **Whitespace**: Use blank lines to separate sections and improve readability. Avoid excessive whitespace.

---
description: 'Documentation and content creation standards'
applyTo: 'README.md'
---

## Language and Structure of README.MD
- Use simple language directed at end-users.
- Be descriptive without being overly technical or complicated.
- Do not assume users have technical skills or knowledge.
- Do not assume users have prior knowledge of this project or its inner workings.
- Anything about environment variables, testing, development, and the more technical aspects of the project should come at the end of the document.