---
layout: page
title: Publications
---

{% assign publication_sections = site.data.publications.sections %}
{% for section in publication_sections %}
{% if section.items and section.items.size > 0 %}
## {{ section.title }}

<ol>
{% for item in section.items %}
  <li>{{ item.display_html }}</li>
{% endfor %}
</ol>
{% endif %}
{% endfor %}

<embed src="files/Award_MIRU2021_reviewer.pdf" type="application/pdf" style="width:500px;height:500px;">

<img src="files/Award_VRST2018_HonorableMentionPoster.jpg" alt="VRST 2018 Honorable Mention (Poster&Demo)" style="width:300px;" />

<embed src="files/Award_MIRU2018_reviewer.pdf" type="application/pdf" style="width:500px;height:500px;">
