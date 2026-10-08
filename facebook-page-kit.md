# Facebook Page kit: Performance Edge Training + Gym Design

Copy and settings for the Facebook Page, built from madefromeffort.com so claims match the site. Instagram: @scottschrat. Site: https://www.madefromeffort.com

## 1. Page basics (Page > Edit Page Info)

| Field | Value |
|---|---|
| Page name | Performance Edge Training + Gym Design |
| Username (@handle) | @madefromeffort (fall back to @performanceedgegyms if taken) |
| Category | Interior Designer (primary), add Personal Trainer and Gym/Physical Fitness Center only if offered |
| Website | https://www.madefromeffort.com |
| Service area | Nassau and Suffolk counties, NY (set as service area, not a street address); select projects nationwide |
| Action button | "Send message" or "Learn more" linked to https://www.madefromeffort.com/contact.html?utm_source=facebook&utm_medium=organic&utm_campaign=page_button |
| Instagram | Link @scottschrat under Settings > Linked accounts |

Short intro (101 characters max): `Luxury home, yacht & estate gym design on Long Island. Led by Scott Schratwieser, CSCS.`

## 2. About text

**Long version**

Performance Edge Training + Gym Design plans private home and estate gyms, yacht and marine training spaces, and select commercial, boutique-studio and country-club fitness projects. Based on Long Island, New York.

Led by Scott Schratwieser, CSCS. Scott trained at Equinox for nearly a decade, including time as a Master Instructor, and still coaches private clients. That coaching background shapes the design work: layout, circulation, storage, finishes and lighting all decide whether a room supports how someone actually trains.

Selected work: Jericho estate gym and sauna, Sands Point, Lloyd Harbor, Oyster Bay Cove and Dix Hills home gyms, a Jupiter Island, FL estate, and the onboard wellness system for M/Y Canoe Canoe.

Private and remote performance coaching is offered separately.

Start a project: https://www.madefromeffort.com/contact.html
Journal: https://www.madefromeffort.com/journal/

## 3. Images

- **Profile photo:** a clean logo or portrait of Scott. Square, shows well when cropped to a circle.
- **Cover photo (820x312 desktop, keep text in the center 640px for mobile):** use a wide project photo already in the repo: `jupiter-island-room-wide.jpg`, `oyster-bay-cove-hero-wide.jpg`, `sands-point-cardio-wide.jpg` or `jericho-room-wide.jpg`. Add the one line "Gym design built around how you train."
- **Featured/pinned content:** see section 5.

Do not use `glen-cove-*` renders as completed work. The site labels Glen Cove a mid-project design study.

## 4. Services list (Page > Services)

1. Private residence & estate gym design: layout, equipment planning, finishes, integration with the home. (residential-gym-design.html)
2. Yacht & marine gym design: space-constrained, motion-aware training environments. (yacht-gym-design.html)
3. Commercial gym & boutique studio design (select projects). (commercial-gym-design.html)
4. Country-club fitness design and modernization audit (select projects). (country-club-fitness-design.html)
5. Private & remote performance coaching (separate service). (training.html)

Do not list prices. The site only offers a directional estimator at /estimator.html.

## 5. Pinned post

> A good gym starts with the room and how you want to use it, not the equipment list.
>
> Performance Edge Training + Gym Design plans private home gyms across Long Island, plus yacht, estate and select commercial projects. See completed work and design studies here:
> https://www.madefromeffort.com/residential-gym-design.html?utm_source=facebook&utm_medium=organic&utm_campaign=pinned_post
>
> Planning a space? Tell us about it: https://www.madefromeffort.com/contact.html?utm_source=facebook&utm_medium=organic&utm_campaign=pinned_post

## 6. Posting workflow: one piece of work, three destinations

For every project photo set or Journal issue:

1. Post natively on Instagram (@scottschrat). Use Reels or carousels.
2. Turn on cross-posting to the Facebook Page (Meta Accounts Center > Sharing across profiles), or use Meta Business Suite to schedule both.
3. For Journal issues, post a Facebook link post to the article. Add `?utm_source=facebook&utm_medium=organic&utm_campaign=journal` to the URL.

Weekly cadence that matches the repo's content slots: Mon gym design, Thu mindset, Sun podcast-inspired idea (the repo already drafts these in `posts/`). Add 1 project photo or short video post per week from the portfolio.

Post templates:

- **Project spotlight:** `[Project], [town]. [One sentence on the problem the room solved.] [One sentence on a design decision.] Full project: [project page URL with UTMs]`
- **Journal share:** the post's excerpt plus link.
- **Before/after or layout:** 3 to 5 images, caption names what changed and why.

Label status accurately: "completed," "in progress," or "design study," as the site does. Credit partners (Paragon Studio, Chill Bunny Wellness) as in `outreach-kit.md`. Don't post client names, addresses or identifiable faces without permission.

## 7. Getting ready for paid ads

What's already in place: GA4 (`G-MVF11QSSPG`) with first-touch UTM capture in `site-events.js`, and a contact form.

What's missing, in order:

1. **Meta Business Suite + Business Manager account.** Create at business.facebook.com, add the Page and the Instagram account, and add a payment method. Only you can do this (it needs your login and billing).
2. **Meta Pixel / Conversions API.** There is no Meta Pixel on the site today. After you create the pixel in Events Manager, send me the Pixel ID and I'll add it to `site-events.js` with a `Lead` event on the contact form submit and `ViewContent` on service pages. Verify the domain in Business Settings > Brand Safety > Domains. The privacy page also needs a line about Meta advertising cookies. I can write that once the pixel exists.
3. **Landing pages per ad:** residential (`residential-gym-design.html`), yacht (`yacht-gym-design.html`), or contact. Use unique UTMs per ad: `utm_source=facebook&utm_medium=paid&utm_campaign=<name>&utm_content=<creative>`.
4. **First campaign (recommended):** Leads or Traffic objective, Long Island geo-radius (Nassau and Suffolk), ages 35 to 65, homeowners. Interests such as luxury home renovation, interior design and home gym are starting points. Budget $15 to $25 per day for 2 weeks, with 2 or 3 creatives (a wide project photo, a short Reel, and a carousel). Judge by cost per inquiry, not clicks.
5. **Ad policy:** don't make outcome or health claims, and don't use before/after body imagery. Housing-style special categories don't apply here, but keep copy to design services.

## 8. Checklist

- [ ] Page name, handle, category, intro, About pasted in
- [ ] Profile and cover photo uploaded
- [ ] Website, contact button and Instagram linked
- [ ] Services added
- [ ] Pinned post published
- [ ] Cross-posting from Instagram on
- [ ] Business Manager set up, payment method added
- [ ] Pixel created, ID sent to Claude for site install
- [ ] First ad campaign drafted

## 9. Status of the live Page (from the Codex session log)

Done by Codex in the browser: bio updated to current gym-design work, design markets and the separate coaching offer listed, fixed "$$" price label removed.

Still open, and what to do:

1. **Page name.** Meta accepted "Performance Edge Training + Gym Design" for review but needs your Facebook password to submit. Re-open Page settings > Page name and confirm.
2. **Cover photo.** Upload `social/facebook-cover-jupiter.jpg` (1640x624, recommended). Alternates: `facebook-cover-jericho.jpg`, `facebook-cover-oyster-bay.jpg` (Scott in the garage gym; better as a profile/about image).
3. **Action button and website link.** They still point to the old online coaching offer. Set the button to "Send message" or "Learn more" and use the contact URL in section 1.
4. **Contacts.** The Page still shows 516-330-1348 and performanceedge.ny@gmail.com. Keep them only if they are current public business contacts.
5. **Intro post** (below), then pin it.

### Intro post

> Performance Edge Training + Gym Design has a new look, and a clearer focus.
>
> We plan private home and estate gyms, yacht and marine training spaces, and select commercial, boutique-studio and country-club fitness projects. Based on Long Island, NY, led by Scott Schratwieser, CSCS.
>
> Private and remote performance coaching is still available, as a separate service.
>
> See the work: https://www.madefromeffort.com/residential-gym-design.html?utm_source=facebook&utm_medium=organic&utm_campaign=intro_post
> Start a project: https://www.madefromeffort.com/contact.html?utm_source=facebook&utm_medium=organic&utm_campaign=intro_post
>
> Photo: Jupiter Island, FL estate gym.

Attach `jupiter-island-room-wide.jpg` or a 3-image carousel from the Jericho, Jupiter Island and Sands Point projects.
