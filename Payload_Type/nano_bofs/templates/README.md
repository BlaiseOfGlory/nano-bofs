This directory is for optional Mythic-installed template overrides and custom templates.

Default nano-bofs templates are maintained in the repo-root `templates/` tree and are baked into the Docker image at:

- `/opt/nano-bofs-base/templates`

At runtime, the payload-side template loader checks this mounted directory before falling back to the baked-in standard templates. That means:

- dropping a new template here makes it available without rebuilding the image
- using the same template name here overrides the baked-in standard template

For standard nano-bofs development, edit the repo-root `templates/` tree instead of adding files here.
