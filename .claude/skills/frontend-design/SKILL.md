---
name: frontend-design
description: >
  Creates distinctive, production-grade frontend interfaces that avoid generic
  AI aesthetics. Use when the user asks to build web components, pages,
  artifacts, dashboards, React components, HTML/CSS layouts, landing pages,
  posters, or any web UI. Also use when the user says "build me a page,"
  "make this look better," "redesign this," "style this," "create a
  component," or uploads a screenshot and expects a rebuild. If the task
  produces HTML, CSS, JSX, or any visual web output, this skill applies.
  Generates creative, polished code with exceptional attention to aesthetic
  detail. Never produces generic output.
---

# Frontend Design

## Rules

IF the user asks for any web UI:
THEN commit to a bold aesthetic direction before writing code. Do not
default to safe choices.

IF the user does not specify a style:
THEN infer from the context. A civic data tool gets editorial density.
A personal project gets personality. A professional deliverable gets
institutional restraint. State the chosen direction in one sentence
and proceed.

IF the user rejects the aesthetic ("AI slop," "predictable," "boring"):
THEN rebuild from scratch with a different direction. Do not iterate
on the rejected direction.

## Typography

Never use Inter, Roboto, Arial, or system-ui as a design choice. These
are fallbacks, not typography. Choose distinctive, characterful fonts.
Pair a display face with a body face. Self-host when possible.

## Color

Commit to a cohesive palette. Dominant color with sharp accent outperforms
evenly distributed palettes. Use CSS variables for consistency. No purple
gradients on white backgrounds.

## Layout

Unexpected layouts. Asymmetry. Overlap. Diagonal flow. Grid-breaking
elements. Generous negative space OR controlled density. The choice must
be intentional, not defaulted.

## Motion

CSS-only solutions for HTML. Motion library for React. Focus on one
well-orchestrated page load with staggered reveals. Do not scatter
micro-interactions randomly.

## Backgrounds

Create atmosphere. Gradient meshes, noise textures, geometric patterns,
layered transparencies, dramatic shadows, decorative borders, grain
overlays. No flat solid backgrounds unless the design specifically
demands brutalist restraint.

## Implementation

Production-grade. Functional. Responsive. Accessible. Every design must
be different from the last. No convergence on common choices across
generations.
