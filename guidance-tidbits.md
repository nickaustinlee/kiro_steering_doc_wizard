Product: 
A guided Python-based CLI which walks the user through creating steering documents for Kiro development, for Python development only.

How do you want to test your program locally? 
<Include some options like Docker, Pytest, etc...>

Do you have a Github repo set up for this project? If so, what's the URL? 
<allow user to copy-paste the github URL>

Do you want to test your code with Github actions too? 
<Yes/No>

Any code formatting rules? 
1. Using black formatter
2. Google.io styleguide (https://google.github.io/styleguide/pyguide.html)
3. Use Black for formatting, but use a linter (e.g. pylint) to enforce Google's python logic rules while ignoring formatting, since Black will take care of that.
4. Other (Please provide detail)

If the user selects 3, they can type instructions into the CLI and hit enter. 

The above responses and values are logged into development-guidelines.md which is placed in the .kiro/steering folder. 

Virtualization? 
1. venv 
2. Poetry
3. Use Poetry for development, but include instructions for venv in our docs too.

llm-guidance.md (which is auto-generated and placed in .kiro/steering) after running the above: 

*The current date is**: <get the local date> (YYYY-MM-DD)

Your training may predate this date, but you should know it's actually the above date and your assumptions about packages or EOLs should be adjusted to reflect that we're in the current date.

**Efficient Working Style**: Don't waste my time by reading one file at a time and coming back and saying, "Oh I need this other file." Just read many files at once or the entire code-base and reduce the number of hops you take to get tasks done.

**Constructive Feedback / Challenge**: Don't take everything I say as gospel. You are welcome to question the logic or suggest better ideas, or ask for clarification if something is unclear. Think of us as a team, and together we're trying to build the best product we can.

**Start Working (in Autopilot mode) only if It's Obvious I Want You To**: Sometimes I ask you what-if questions or hypotheticals to flesh out an idea. In these cases, you don't need to immediately start coding it up or editing files. If I haven't given you an affirmative order to do something, you should ask if I'd like for you to change something.
