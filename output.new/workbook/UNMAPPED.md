# Unmapped tiles

These tiles were captured but could not be attributed to a (channel, device) pair, so they are **missing** from the data*.py files.
Nothing was guessed and nothing was defaulted to 0.

Fix either by tuning `CHANNEL_PATTERNS` / `DEVICE_PATTERNS` in `looker_capture/config.py`, or by passing `--layout-map` with an explicit tile-index -> [channel, device] mapping per page.

| page | period | landing group | tile | kind | title | value | why |
|---|---|---|---|---|---|---|---|
| sessions | current | All landing pages | 17 | scorecard | Total sessions - Newsletter traffic | 7,455 | channel 'Newsletter' has no column in the workbook |
| sessions | current | All landing pages | 18 | scorecard | Mobile Total sessions - Newsletter | 4,927 | channel 'Newsletter' has no column in the workbook |
| sessions | current | All landing pages | 19 | scorecard | Desktop Total sessions - Newsletter | 2,316 | channel 'Newsletter' has no column in the workbook |
| sessions | current | All landing pages | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| sessions | current | All landing pages | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| sessions | current | Home page | 17 | scorecard | Total sessions - Newsletter traffic | 6,280 | channel 'Newsletter' has no column in the workbook |
| sessions | current | Home page | 18 | scorecard | Mobile Total sessions - Newsletter | 4,287 | channel 'Newsletter' has no column in the workbook |
| sessions | current | Home page | 19 | scorecard | Desktop Total sessions - Newsletter | 1,880 | channel 'Newsletter' has no column in the workbook |
| sessions | current | Home page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| sessions | current | Home page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| sessions | current | Airport page | 17 | scorecard | Total sessions - Newsletter traffic | 469 | channel 'Newsletter' has no column in the workbook |
| sessions | current | Airport page | 18 | scorecard | Mobile Total sessions - Newsletter | 240 | channel 'Newsletter' has no column in the workbook |
| sessions | current | Airport page | 19 | scorecard | Desktop Total sessions - Newsletter | 218 | channel 'Newsletter' has no column in the workbook |
| sessions | current | Airport page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| sessions | current | Airport page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| sessions | current | Route page | 17 | scorecard | Total sessions - Newsletter traffic | 278 | channel 'Newsletter' has no column in the workbook |
| sessions | current | Route page | 18 | scorecard | Mobile Total sessions - Newsletter | 164 | channel 'Newsletter' has no column in the workbook |
| sessions | current | Route page | 19 | scorecard | Desktop Total sessions - Newsletter | 108 | channel 'Newsletter' has no column in the workbook |
| sessions | current | Route page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| sessions | current | Route page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| sessions | prior | All landing pages | 17 | scorecard | Total sessions - Newsletter traffic | 14,343 | channel 'Newsletter' has no column in the workbook |
| sessions | prior | All landing pages | 18 | scorecard | Mobile Total sessions - Newsletter | 8,689 | channel 'Newsletter' has no column in the workbook |
| sessions | prior | All landing pages | 19 | scorecard | Desktop Total sessions - Newsletter | 5,330 | channel 'Newsletter' has no column in the workbook |
| sessions | prior | All landing pages | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| sessions | prior | All landing pages | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| sessions | prior | Home page | 17 | scorecard | Total sessions - Newsletter traffic | 12,941 | channel 'Newsletter' has no column in the workbook |
| sessions | prior | Home page | 18 | scorecard | Mobile Total sessions - Newsletter | 7,798 | channel 'Newsletter' has no column in the workbook |
| sessions | prior | Home page | 19 | scorecard | Desktop Total sessions - Newsletter | 4,814 | channel 'Newsletter' has no column in the workbook |
| sessions | prior | Home page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| sessions | prior | Home page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| sessions | prior | Airport page | 17 | scorecard | Total sessions - Newsletter traffic | 460 | channel 'Newsletter' has no column in the workbook |
| sessions | prior | Airport page | 18 | scorecard | Mobile Total sessions - Newsletter | 323 | channel 'Newsletter' has no column in the workbook |
| sessions | prior | Airport page | 19 | scorecard | Desktop Total sessions - Newsletter | 131 | channel 'Newsletter' has no column in the workbook |
| sessions | prior | Airport page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| sessions | prior | Airport page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| sessions | prior | Route page | 17 | scorecard | Total sessions - Newsletter traffic | 192 | channel 'Newsletter' has no column in the workbook |
| sessions | prior | Route page | 18 | scorecard | Mobile Total sessions - Newsletter | 150 | channel 'Newsletter' has no column in the workbook |
| sessions | prior | Route page | 19 | scorecard | Desktop Total sessions - Newsletter | 40 | channel 'Newsletter' has no column in the workbook |
| sessions | prior | Route page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| sessions | prior | Route page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| start_search | current | All landing pages | 17 | scorecard | Desktop Submit Search - Org | 15,873 | scorecard 'Desktop Submit Search - Org' is not this page's metric (expected /\bstart\s*search\b/) |
| start_search | current | All landing pages | 18 | scorecard | Start Search - Newsletter traffic | 4,291 | channel 'Newsletter' has no column in the workbook |
| start_search | current | All landing pages | 19 | scorecard | Mobile Start Search - Newsletter | 2,908 | channel 'Newsletter' has no column in the workbook |
| start_search | current | All landing pages | 20 | scorecard | Desktop Start Search - Newsletter | 1,266 | channel 'Newsletter' has no column in the workbook |
| start_search | current | All landing pages | 21 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| start_search | current | All landing pages | 22 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| start_search | current | Home page | 17 | scorecard | Desktop Submit Search - Org | 2,649 | scorecard 'Desktop Submit Search - Org' is not this page's metric (expected /\bstart\s*search\b/) |
| start_search | current | Home page | 18 | scorecard | Start Search - Newsletter traffic | 3,670 | channel 'Newsletter' has no column in the workbook |
| start_search | current | Home page | 19 | scorecard | Mobile Start Search - Newsletter | 2,647 | channel 'Newsletter' has no column in the workbook |
| start_search | current | Home page | 20 | scorecard | Desktop Start Search - Newsletter | 976 | channel 'Newsletter' has no column in the workbook |
| start_search | current | Home page | 21 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| start_search | current | Home page | 22 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| start_search | current | Airport page | 17 | scorecard | Desktop Submit Search - Org | 3,674 | scorecard 'Desktop Submit Search - Org' is not this page's metric (expected /\bstart\s*search\b/) |
| start_search | current | Airport page | 18 | scorecard | Start Search - Newsletter traffic | 239 | channel 'Newsletter' has no column in the workbook |
| start_search | current | Airport page | 19 | scorecard | Mobile Start Search - Newsletter | 113 | channel 'Newsletter' has no column in the workbook |
| start_search | current | Airport page | 20 | scorecard | Desktop Start Search - Newsletter | 118 | channel 'Newsletter' has no column in the workbook |
| start_search | current | Airport page | 21 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| start_search | current | Airport page | 22 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| start_search | current | Route page | 17 | scorecard | Desktop Submit Search - Org | 7,060 | scorecard 'Desktop Submit Search - Org' is not this page's metric (expected /\bstart\s*search\b/) |
| start_search | current | Route page | 18 | scorecard | Start Search - Newsletter traffic | 130 | channel 'Newsletter' has no column in the workbook |
| start_search | current | Route page | 19 | scorecard | Mobile Start Search - Newsletter | 66 | channel 'Newsletter' has no column in the workbook |
| start_search | current | Route page | 20 | scorecard | Desktop Start Search - Newsletter | 62 | channel 'Newsletter' has no column in the workbook |
| start_search | current | Route page | 21 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| start_search | current | Route page | 22 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| start_search | prior | All landing pages | 17 | scorecard | Desktop Submit Search - Org | 17,333 | scorecard 'Desktop Submit Search - Org' is not this page's metric (expected /\bstart\s*search\b/) |
| start_search | prior | All landing pages | 18 | scorecard | Start Search - Newsletter traffic | 7,340 | channel 'Newsletter' has no column in the workbook |
| start_search | prior | All landing pages | 19 | scorecard | Mobile Start Search - Newsletter | 5,056 | channel 'Newsletter' has no column in the workbook |
| start_search | prior | All landing pages | 20 | scorecard | Desktop Start Search - Newsletter | 2,087 | channel 'Newsletter' has no column in the workbook |
| start_search | prior | All landing pages | 21 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| start_search | prior | All landing pages | 22 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| start_search | prior | Home page | 17 | scorecard | Desktop Submit Search - Org | 3,213 | scorecard 'Desktop Submit Search - Org' is not this page's metric (expected /\bstart\s*search\b/) |
| start_search | prior | Home page | 18 | scorecard | Start Search - Newsletter traffic | 6,665 | channel 'Newsletter' has no column in the workbook |
| start_search | prior | Home page | 19 | scorecard | Mobile Start Search - Newsletter | 4,633 | channel 'Newsletter' has no column in the workbook |
| start_search | prior | Home page | 20 | scorecard | Desktop Start Search - Newsletter | 1,858 | channel 'Newsletter' has no column in the workbook |
| start_search | prior | Home page | 21 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| start_search | prior | Home page | 22 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| start_search | prior | Airport page | 17 | scorecard | Desktop Submit Search - Org | 4,334 | scorecard 'Desktop Submit Search - Org' is not this page's metric (expected /\bstart\s*search\b/) |
| start_search | prior | Airport page | 18 | scorecard | Start Search - Newsletter traffic | 232 | channel 'Newsletter' has no column in the workbook |
| start_search | prior | Airport page | 19 | scorecard | Mobile Start Search - Newsletter | 167 | channel 'Newsletter' has no column in the workbook |
| start_search | prior | Airport page | 20 | scorecard | Desktop Start Search - Newsletter | 61 | channel 'Newsletter' has no column in the workbook |
| start_search | prior | Airport page | 21 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| start_search | prior | Airport page | 22 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| start_search | prior | Route page | 17 | scorecard | Desktop Submit Search - Org | 8,021 | scorecard 'Desktop Submit Search - Org' is not this page's metric (expected /\bstart\s*search\b/) |
| start_search | prior | Route page | 18 | scorecard | Start Search - Newsletter traffic | 131 | channel 'Newsletter' has no column in the workbook |
| start_search | prior | Route page | 19 | scorecard | Mobile Start Search - Newsletter | 110 | channel 'Newsletter' has no column in the workbook |
| start_search | prior | Route page | 20 | scorecard | Desktop Start Search - Newsletter | 19 | channel 'Newsletter' has no column in the workbook |
| start_search | prior | Route page | 21 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| start_search | prior | Route page | 22 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| searches | current | All landing pages | 17 | scorecard | Total Searches - Newsletter traffic | 3,449 | channel 'Newsletter' has no column in the workbook |
| searches | current | All landing pages | 18 | scorecard | Mobile Searches - Newsletter | 2,418 | channel 'Newsletter' has no column in the workbook |
| searches | current | All landing pages | 19 | scorecard | Desktop Searches- Newsletter | 990 | channel 'Newsletter' has no column in the workbook |
| searches | current | All landing pages | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| searches | current | All landing pages | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| searches | current | Home page | 17 | scorecard | Total Searches - Newsletter traffic | 3,078 | channel 'Newsletter' has no column in the workbook |
| searches | current | Home page | 18 | scorecard | Mobile Searches - Newsletter | 2,220 | channel 'Newsletter' has no column in the workbook |
| searches | current | Home page | 19 | scorecard | Desktop Searches- Newsletter | 830 | channel 'Newsletter' has no column in the workbook |
| searches | current | Home page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| searches | current | Home page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| searches | current | Airport page | 17 | scorecard | Total Searches - Newsletter traffic | 189 | channel 'Newsletter' has no column in the workbook |
| searches | current | Airport page | 18 | scorecard | Mobile Searches - Newsletter | 88 | channel 'Newsletter' has no column in the workbook |
| searches | current | Airport page | 19 | scorecard | Desktop Searches- Newsletter | 93 | channel 'Newsletter' has no column in the workbook |
| searches | current | Airport page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| searches | current | Airport page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| searches | current | Route page | 17 | scorecard | Total Searches - Newsletter traffic | 120 | channel 'Newsletter' has no column in the workbook |
| searches | current | Route page | 18 | scorecard | Mobile Searches - Newsletter | 66 | channel 'Newsletter' has no column in the workbook |
| searches | current | Route page | 19 | scorecard | Desktop Searches- Newsletter | 52 | channel 'Newsletter' has no column in the workbook |
| searches | current | Route page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| searches | current | Route page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| searches | prior | All landing pages | 17 | scorecard | Total Searches - Newsletter traffic | 6,138 | channel 'Newsletter' has no column in the workbook |
| searches | prior | All landing pages | 18 | scorecard | Mobile Searches - Newsletter | 4,164 | channel 'Newsletter' has no column in the workbook |
| searches | prior | All landing pages | 19 | scorecard | Desktop Searches- Newsletter | 1,778 | channel 'Newsletter' has no column in the workbook |
| searches | prior | All landing pages | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| searches | prior | All landing pages | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| searches | prior | Home page | 17 | scorecard | Total Searches - Newsletter traffic | 5,628 | channel 'Newsletter' has no column in the workbook |
| searches | prior | Home page | 18 | scorecard | Mobile Searches - Newsletter | 3,807 | channel 'Newsletter' has no column in the workbook |
| searches | prior | Home page | 19 | scorecard | Desktop Searches- Newsletter | 1,665 | channel 'Newsletter' has no column in the workbook |
| searches | prior | Home page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| searches | prior | Home page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| searches | prior | Airport page | 17 | scorecard | Total Searches - Newsletter traffic | 219 | channel 'Newsletter' has no column in the workbook |
| searches | prior | Airport page | 18 | scorecard | Mobile Searches - Newsletter | 148 | channel 'Newsletter' has no column in the workbook |
| searches | prior | Airport page | 19 | scorecard | Desktop Searches- Newsletter | 67 | channel 'Newsletter' has no column in the workbook |
| searches | prior | Airport page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| searches | prior | Airport page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| searches | prior | Route page | 17 | scorecard | Total Searches - Newsletter traffic | 119 | channel 'Newsletter' has no column in the workbook |
| searches | prior | Route page | 18 | scorecard | Mobile Searches - Newsletter | 92 | channel 'Newsletter' has no column in the workbook |
| searches | prior | Route page | 19 | scorecard | Desktop Searches- Newsletter | 25 | channel 'Newsletter' has no column in the workbook |
| searches | prior | Route page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| searches | prior | Route page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| select_item | current | All landing pages | 17 | scorecard | Total Select item - Newsletter traffic | 1,053 | channel 'Newsletter' has no column in the workbook |
| select_item | current | All landing pages | 18 | scorecard | Mobile Select item - Newsletter | 706 | channel 'Newsletter' has no column in the workbook |
| select_item | current | All landing pages | 19 | scorecard | Desktop Select item - Newsletter | 328 | channel 'Newsletter' has no column in the workbook |
| select_item | current | All landing pages | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| select_item | current | All landing pages | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| select_item | current | Home page | 17 | scorecard | Total Select item - Newsletter traffic | 966 | channel 'Newsletter' has no column in the workbook |
| select_item | current | Home page | 18 | scorecard | Mobile Select item - Newsletter | 657 | channel 'Newsletter' has no column in the workbook |
| select_item | current | Home page | 19 | scorecard | Desktop Select item - Newsletter | 289 | channel 'Newsletter' has no column in the workbook |
| select_item | current | Home page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| select_item | current | Home page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| select_item | current | Airport page | 17 | scorecard | Total Select item - Newsletter traffic | 43 | channel 'Newsletter' has no column in the workbook |
| select_item | current | Airport page | 18 | scorecard | Mobile Select item - Newsletter | 21 | channel 'Newsletter' has no column in the workbook |
| select_item | current | Airport page | 19 | scorecard | Desktop Select item - Newsletter | 22 | channel 'Newsletter' has no column in the workbook |
| select_item | current | Airport page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| select_item | current | Airport page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| select_item | current | Route page | 17 | scorecard | Total Select item - Newsletter traffic | 18 | channel 'Newsletter' has no column in the workbook |
| select_item | current | Route page | 18 | scorecard | Mobile Select item - Newsletter | 11 | channel 'Newsletter' has no column in the workbook |
| select_item | current | Route page | 19 | scorecard | Desktop Select item - Newsletter | 7 | channel 'Newsletter' has no column in the workbook |
| select_item | current | Route page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| select_item | current | Route page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| select_item | prior | All landing pages | 17 | scorecard | Total Select item - Newsletter traffic | 2,089 | channel 'Newsletter' has no column in the workbook |
| select_item | prior | All landing pages | 18 | scorecard | Mobile Select item - Newsletter | 1,341 | channel 'Newsletter' has no column in the workbook |
| select_item | prior | All landing pages | 19 | scorecard | Desktop Select item - Newsletter | 695 | channel 'Newsletter' has no column in the workbook |
| select_item | prior | All landing pages | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| select_item | prior | All landing pages | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| select_item | prior | Home page | 17 | scorecard | Total Select item - Newsletter traffic | 1,952 | channel 'Newsletter' has no column in the workbook |
| select_item | prior | Home page | 18 | scorecard | Mobile Select item - Newsletter | 1,255 | channel 'Newsletter' has no column in the workbook |
| select_item | prior | Home page | 19 | scorecard | Desktop Select item - Newsletter | 652 | channel 'Newsletter' has no column in the workbook |
| select_item | prior | Home page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| select_item | prior | Home page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| select_item | prior | Airport page | 17 | scorecard | Total Select item - Newsletter traffic | 67 | channel 'Newsletter' has no column in the workbook |
| select_item | prior | Airport page | 18 | scorecard | Mobile Select item - Newsletter | 36 | channel 'Newsletter' has no column in the workbook |
| select_item | prior | Airport page | 19 | scorecard | Desktop Select item - Newsletter | 28 | channel 'Newsletter' has no column in the workbook |
| select_item | prior | Airport page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| select_item | prior | Airport page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| select_item | prior | Route page | 17 | scorecard | Total Select item - Newsletter traffic | 29 | channel 'Newsletter' has no column in the workbook |
| select_item | prior | Route page | 18 | scorecard | Mobile Select item - Newsletter | 21 | channel 'Newsletter' has no column in the workbook |
| select_item | prior | Route page | 19 | scorecard | Desktop Select item - Newsletter | 8 | channel 'Newsletter' has no column in the workbook |
| select_item | prior | Route page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| select_item | prior | Route page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| add_to_cart | current | All landing pages | 17 | scorecard | Total Add to cart - Newsletter traffic | 881 | channel 'Newsletter' has no column in the workbook |
| add_to_cart | current | All landing pages | 18 | scorecard | Mobile Add to cart - Newsletter | 573 | channel 'Newsletter' has no column in the workbook |
| add_to_cart | current | All landing pages | 19 | scorecard | Desktop Add to cart- Newsletter | 289 | channel 'Newsletter' has no column in the workbook |
| add_to_cart | current | All landing pages | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| add_to_cart | current | All landing pages | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| add_to_cart | current | Home page | 17 | scorecard | Total Add to cart - Newsletter traffic | 801 | channel 'Newsletter' has no column in the workbook |
| add_to_cart | current | Home page | 18 | scorecard | Mobile Add to cart - Newsletter | 531 | channel 'Newsletter' has no column in the workbook |
| add_to_cart | current | Home page | 19 | scorecard | Desktop Add to cart- Newsletter | 252 | channel 'Newsletter' has no column in the workbook |
| add_to_cart | current | Home page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| add_to_cart | current | Home page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| add_to_cart | current | Airport page | 17 | scorecard | Total Add to cart - Newsletter traffic | 35 | channel 'Newsletter' has no column in the workbook |
| add_to_cart | current | Airport page | 18 | scorecard | Mobile Add to cart - Newsletter | 17 | channel 'Newsletter' has no column in the workbook |
| add_to_cart | current | Airport page | 19 | scorecard | Desktop Add to cart- Newsletter | 18 | channel 'Newsletter' has no column in the workbook |
| add_to_cart | current | Airport page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| add_to_cart | current | Airport page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| add_to_cart | current | Route page | 17 | scorecard | Total Add to cart - Newsletter traffic | 16 | channel 'Newsletter' has no column in the workbook |
| add_to_cart | current | Route page | 18 | scorecard | Mobile Add to cart - Newsletter | 11 | channel 'Newsletter' has no column in the workbook |
| add_to_cart | current | Route page | 19 | scorecard | Desktop Add to cart- Newsletter | 5 | channel 'Newsletter' has no column in the workbook |
| add_to_cart | current | Route page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| add_to_cart | current | Route page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| add_to_cart | prior | All landing pages | 17 | scorecard | Total Add to cart - Newsletter traffic | 1,815 | channel 'Newsletter' has no column in the workbook |
| add_to_cart | prior | All landing pages | 18 | scorecard | Mobile Add to cart - Newsletter | 1,159 | channel 'Newsletter' has no column in the workbook |
| add_to_cart | prior | All landing pages | 19 | scorecard | Desktop Add to cart- Newsletter | 607 | channel 'Newsletter' has no column in the workbook |
| add_to_cart | prior | All landing pages | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| add_to_cart | prior | All landing pages | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| add_to_cart | prior | Home page | 17 | scorecard | Total Add to cart - Newsletter traffic | 1,702 | channel 'Newsletter' has no column in the workbook |
| add_to_cart | prior | Home page | 18 | scorecard | Mobile Add to cart - Newsletter | 1,089 | channel 'Newsletter' has no column in the workbook |
| add_to_cart | prior | Home page | 19 | scorecard | Desktop Add to cart- Newsletter | 572 | channel 'Newsletter' has no column in the workbook |
| add_to_cart | prior | Home page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| add_to_cart | prior | Home page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| add_to_cart | prior | Airport page | 17 | scorecard | Total Add to cart - Newsletter traffic | 49 | channel 'Newsletter' has no column in the workbook |
| add_to_cart | prior | Airport page | 18 | scorecard | Mobile Add to cart - Newsletter | 27 | channel 'Newsletter' has no column in the workbook |
| add_to_cart | prior | Airport page | 19 | scorecard | Desktop Add to cart- Newsletter | 20 | channel 'Newsletter' has no column in the workbook |
| add_to_cart | prior | Airport page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| add_to_cart | prior | Airport page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| add_to_cart | prior | Route page | 17 | scorecard | Total Add to cart - Newsletter traffic | 29 | channel 'Newsletter' has no column in the workbook |
| add_to_cart | prior | Route page | 18 | scorecard | Mobile Add to cart - Newsletter | 22 | channel 'Newsletter' has no column in the workbook |
| add_to_cart | prior | Route page | 19 | scorecard | Desktop Add to cart- Newsletter | 7 | channel 'Newsletter' has no column in the workbook |
| add_to_cart | prior | Route page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| add_to_cart | prior | Route page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| begin_checkout | current | All landing pages | 17 | scorecard | Total Begin Checkout - Newsletter traffi | 526 | channel 'Newsletter' has no column in the workbook |
| begin_checkout | current | All landing pages | 18 | scorecard | Mobile Begin Checkout - Newsletter | 317 | channel 'Newsletter' has no column in the workbook |
| begin_checkout | current | All landing pages | 19 | scorecard | Desktop Begin Checkout - Newsletter | 195 | channel 'Newsletter' has no column in the workbook |
| begin_checkout | current | All landing pages | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| begin_checkout | current | All landing pages | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| begin_checkout | current | Home page | 17 | scorecard | Total Begin Checkout - Newsletter traffi | 490 | channel 'Newsletter' has no column in the workbook |
| begin_checkout | current | Home page | 18 | scorecard | Mobile Begin Checkout - Newsletter | 293 | channel 'Newsletter' has no column in the workbook |
| begin_checkout | current | Home page | 19 | scorecard | Desktop Begin Checkout - Newsletter | 184 | channel 'Newsletter' has no column in the workbook |
| begin_checkout | current | Home page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| begin_checkout | current | Home page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| begin_checkout | current | Airport page | 17 | scorecard | Total Begin Checkout - Newsletter traffi | 12 | channel 'Newsletter' has no column in the workbook |
| begin_checkout | current | Airport page | 18 | scorecard | Mobile Begin Checkout - Newsletter | 7 | channel 'Newsletter' has no column in the workbook |
| begin_checkout | current | Airport page | 19 | scorecard | Desktop Begin Checkout - Newsletter | 5 | channel 'Newsletter' has no column in the workbook |
| begin_checkout | current | Airport page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| begin_checkout | current | Airport page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| begin_checkout | current | Route page | 17 | scorecard | Total Begin Checkout - Newsletter traffi | 5 | channel 'Newsletter' has no column in the workbook |
| begin_checkout | current | Route page | 18 | scorecard | Mobile Begin Checkout - Newsletter | 4 | channel 'Newsletter' has no column in the workbook |
| begin_checkout | current | Route page | 19 | scorecard | Desktop Begin Checkout - Newsletter | 1 | channel 'Newsletter' has no column in the workbook |
| begin_checkout | current | Route page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| begin_checkout | current | Route page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| begin_checkout | prior | All landing pages | 17 | scorecard | Total Begin Checkout - Newsletter traffi | 1,157 | channel 'Newsletter' has no column in the workbook |
| begin_checkout | prior | All landing pages | 18 | scorecard | Mobile Begin Checkout - Newsletter | 681 | channel 'Newsletter' has no column in the workbook |
| begin_checkout | prior | All landing pages | 19 | scorecard | Desktop Begin Checkout - Newsletter | 446 | channel 'Newsletter' has no column in the workbook |
| begin_checkout | prior | All landing pages | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| begin_checkout | prior | All landing pages | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| begin_checkout | prior | Home page | 17 | scorecard | Total Begin Checkout - Newsletter traffi | 1,099 | channel 'Newsletter' has no column in the workbook |
| begin_checkout | prior | Home page | 18 | scorecard | Mobile Begin Checkout - Newsletter | 645 | channel 'Newsletter' has no column in the workbook |
| begin_checkout | prior | Home page | 19 | scorecard | Desktop Begin Checkout - Newsletter | 427 | channel 'Newsletter' has no column in the workbook |
| begin_checkout | prior | Home page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| begin_checkout | prior | Home page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| begin_checkout | prior | Airport page | 17 | scorecard | Total Begin Checkout - Newsletter traffi | 15 | channel 'Newsletter' has no column in the workbook |
| begin_checkout | prior | Airport page | 18 | scorecard | Mobile Begin Checkout - Newsletter | 4 | channel 'Newsletter' has no column in the workbook |
| begin_checkout | prior | Airport page | 19 | scorecard | Desktop Begin Checkout - Newsletter | 11 | channel 'Newsletter' has no column in the workbook |
| begin_checkout | prior | Airport page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| begin_checkout | prior | Airport page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| begin_checkout | prior | Route page | 17 | scorecard | Total Begin Checkout - Newsletter traffi | 15 | channel 'Newsletter' has no column in the workbook |
| begin_checkout | prior | Route page | 18 | scorecard | Mobile Begin Checkout - Newsletter | 12 | channel 'Newsletter' has no column in the workbook |
| begin_checkout | prior | Route page | 19 | scorecard | Desktop Begin Checkout - Newsletter | 3 | channel 'Newsletter' has no column in the workbook |
| begin_checkout | prior | Route page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| begin_checkout | prior | Route page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| purchases | current | All landing pages | 17 | scorecard | Total Purchases - Newsletter | 455 | channel 'Newsletter' has no column in the workbook |
| purchases | current | All landing pages | 18 | scorecard | Mobile Purchases - Newsletter | 273 | channel 'Newsletter' has no column in the workbook |
| purchases | current | All landing pages | 19 | scorecard | Desktop Purchases - Newsletter | 170 | channel 'Newsletter' has no column in the workbook |
| purchases | current | All landing pages | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| purchases | current | All landing pages | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| purchases | current | Home page | 17 | scorecard | Total Purchases - Newsletter | 406 | channel 'Newsletter' has no column in the workbook |
| purchases | current | Home page | 18 | scorecard | Mobile Purchases - Newsletter | 240 | channel 'Newsletter' has no column in the workbook |
| purchases | current | Home page | 19 | scorecard | Desktop Purchases - Newsletter | 155 | channel 'Newsletter' has no column in the workbook |
| purchases | current | Home page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| purchases | current | Home page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| purchases | current | Airport page | 17 | scorecard | Total Purchases - Newsletter | 9 | channel 'Newsletter' has no column in the workbook |
| purchases | current | Airport page | 18 | scorecard | Mobile Purchases - Newsletter | 6 | channel 'Newsletter' has no column in the workbook |
| purchases | current | Airport page | 19 | scorecard | Desktop Purchases - Newsletter | 3 | channel 'Newsletter' has no column in the workbook |
| purchases | current | Airport page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| purchases | current | Airport page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| purchases | current | Route page | 17 | scorecard | Total Purchases - Newsletter | 4 | channel 'Newsletter' has no column in the workbook |
| purchases | current | Route page | 18 | scorecard | Mobile Purchases - Newsletter | 3 | channel 'Newsletter' has no column in the workbook |
| purchases | current | Route page | 19 | scorecard | Desktop Purchases - Newsletter | 1 | channel 'Newsletter' has no column in the workbook |
| purchases | current | Route page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| purchases | current | Route page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| purchases | prior | All landing pages | 17 | scorecard | Total Purchases - Newsletter | 1,013 | channel 'Newsletter' has no column in the workbook |
| purchases | prior | All landing pages | 18 | scorecard | Mobile Purchases - Newsletter | 582 | channel 'Newsletter' has no column in the workbook |
| purchases | prior | All landing pages | 19 | scorecard | Desktop Purchases - Newsletter | 402 | channel 'Newsletter' has no column in the workbook |
| purchases | prior | All landing pages | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| purchases | prior | All landing pages | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| purchases | prior | Home page | 17 | scorecard | Total Purchases - Newsletter | 918 | channel 'Newsletter' has no column in the workbook |
| purchases | prior | Home page | 18 | scorecard | Mobile Purchases - Newsletter | 517 | channel 'Newsletter' has no column in the workbook |
| purchases | prior | Home page | 19 | scorecard | Desktop Purchases - Newsletter | 376 | channel 'Newsletter' has no column in the workbook |
| purchases | prior | Home page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| purchases | prior | Home page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| purchases | prior | Airport page | 17 | scorecard | Total Purchases - Newsletter | 10 | channel 'Newsletter' has no column in the workbook |
| purchases | prior | Airport page | 18 | scorecard | Mobile Purchases - Newsletter | 3 | channel 'Newsletter' has no column in the workbook |
| purchases | prior | Airport page | 19 | scorecard | Desktop Purchases - Newsletter | 7 | channel 'Newsletter' has no column in the workbook |
| purchases | prior | Airport page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| purchases | prior | Airport page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
| purchases | prior | Route page | 17 | scorecard | Total Purchases - Newsletter | 15 | channel 'Newsletter' has no column in the workbook |
| purchases | prior | Route page | 18 | scorecard | Mobile Purchases - Newsletter | 14 | channel 'Newsletter' has no column in the workbook |
| purchases | prior | Route page | 19 | scorecard | Desktop Purchases - Newsletter | 1 | channel 'Newsletter' has no column in the workbook |
| purchases | prior | Route page | 20 | table | country table (Desktop) |  | channel 'Newsletter' has no column in the workbook |
| purchases | prior | Route page | 21 | table | country table (Mobile) |  | channel 'Newsletter' has no column in the workbook |
