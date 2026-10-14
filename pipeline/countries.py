"""The IMF's country codes, mapped to ISO codes and the WEO's analytical groups.

The WEO identifies countries by IMF (IFS) code. The world map needs the ISO
3166 numeric code (the ``id`` of each shape in ``world-atlas``), and the group
comparisons need the WEO classification: advanced economies, and five regions
for emerging market and developing economies (EMDEs).

The classification is the WEO's current one, applied to every year: Croatia,
for example, counts as advanced throughout although it was reclassified in 2023.
Kosovo has no ISO code (``XKX`` is the IMF's), so it has no shape on the map.
"""

from __future__ import annotations

import polars as pl

REGIONS = {
    "adv": "Advanced economies",
    "asia": "Emerging and developing Asia",
    "europe": "Emerging and developing Europe",
    "latam": "Latin America and the Caribbean",
    "meca": "Middle East and Central Asia",
    "ssa": "Sub-Saharan Africa",
}

# IFS code, ISO alpha-3, ISO numeric, WEO group.
_TABLE = """
111 USA 840 adv | 112 GBR 826 adv | 122 AUT 040 adv | 124 BEL 056 adv | 128 DNK 208 adv
132 FRA 250 adv | 134 DEU 276 adv | 135 SMR 674 adv | 136 ITA 380 adv | 137 LUX 442 adv
138 NLD 528 adv | 142 NOR 578 adv | 144 SWE 752 adv | 146 CHE 756 adv | 156 CAN 124 adv
158 JPN 392 adv | 171 AND 020 adv | 172 FIN 246 adv | 174 GRC 300 adv | 176 ISL 352 adv
178 IRL 372 adv | 181 MLT 470 adv | 182 PRT 620 adv | 184 ESP 724 adv | 186 TUR 792 europe
193 AUS 036 adv | 196 NZL 554 adv | 199 ZAF 710 ssa
213 ARG 032 latam | 218 BOL 068 latam | 223 BRA 076 latam | 228 CHL 152 latam | 233 COL 170 latam
238 CRI 188 latam | 243 DOM 214 latam | 248 ECU 218 latam | 253 SLV 222 latam | 258 GTM 320 latam
263 HTI 332 latam | 268 HND 340 latam | 273 MEX 484 latam | 278 NIC 558 latam | 283 PAN 591 latam
288 PRY 600 latam | 293 PER 604 latam | 298 URY 858 latam | 299 VEN 862 latam
311 ATG 028 latam | 313 BHS 044 latam | 314 ABW 533 latam | 316 BRB 052 latam | 321 DMA 212 latam
328 GRD 308 latam | 336 GUY 328 latam | 339 BLZ 084 latam | 343 JAM 388 latam | 359 PRI 630 adv
361 KNA 659 latam | 362 LCA 662 latam | 364 VCT 670 latam | 366 SUR 740 latam | 369 TTO 780 latam
419 BHR 048 meca | 423 CYP 196 adv | 429 IRN 364 meca | 433 IRQ 368 meca | 436 ISR 376 adv
439 JOR 400 meca | 443 KWT 414 meca | 446 LBN 422 meca | 449 OMN 512 meca | 453 QAT 634 meca
456 SAU 682 meca | 463 SYR 760 meca | 466 ARE 784 meca | 469 EGY 818 meca | 474 YEM 887 meca
487 PSE 275 meca
512 AFG 004 meca | 513 BGD 050 asia | 514 BTN 064 asia | 516 BRN 096 asia | 518 MMR 104 asia
522 KHM 116 asia | 524 LKA 144 asia | 528 TWN 158 adv | 532 HKG 344 adv | 534 IND 356 asia
536 IDN 360 asia | 537 TLS 626 asia | 542 KOR 410 adv | 544 LAO 418 asia | 546 MAC 446 adv
548 MYS 458 asia | 556 MDV 462 asia | 558 NPL 524 asia | 564 PAK 586 meca | 565 PLW 585 asia
566 PHL 608 asia | 576 SGP 702 adv | 578 THA 764 asia | 582 VNM 704 asia
611 DJI 262 meca | 612 DZA 012 meca | 614 AGO 024 ssa | 616 BWA 072 ssa | 618 BDI 108 ssa
622 CMR 120 ssa | 624 CPV 132 ssa | 626 CAF 140 ssa | 628 TCD 148 ssa | 632 COM 174 ssa
634 COG 178 ssa | 636 COD 180 ssa | 638 BEN 204 ssa | 642 GNQ 226 ssa | 643 ERI 232 ssa
644 ETH 231 ssa | 646 GAB 266 ssa | 648 GMB 270 ssa | 652 GHA 288 ssa | 654 GNB 624 ssa
656 GIN 324 ssa | 662 CIV 384 ssa | 664 KEN 404 ssa | 666 LSO 426 ssa | 668 LBR 430 ssa
672 LBY 434 meca | 674 MDG 450 ssa | 676 MWI 454 ssa | 678 MLI 466 ssa | 682 MRT 478 meca
684 MUS 480 ssa | 686 MAR 504 meca | 688 MOZ 508 ssa | 692 NER 562 ssa | 694 NGA 566 ssa
698 ZWE 716 ssa | 714 RWA 646 ssa | 716 STP 678 ssa | 718 SYC 690 ssa | 722 SEN 686 ssa
724 SLE 694 ssa | 726 SOM 706 meca | 728 NAM 516 ssa | 732 SDN 729 meca | 733 SSD 728 ssa
734 SWZ 748 ssa | 738 TZA 834 ssa | 742 TGO 768 ssa | 744 TUN 788 meca | 746 UGA 800 ssa
748 BFA 854 ssa | 754 ZMB 894 ssa
813 SLB 090 asia | 819 FJI 242 asia | 826 KIR 296 asia | 836 NRU 520 asia | 846 VUT 548 asia
853 PNG 598 asia | 862 WSM 882 asia | 866 TON 776 asia | 867 MHL 584 asia | 868 FSM 583 asia
869 TUV 798 asia
911 ARM 051 meca | 912 AZE 031 meca | 913 BLR 112 europe | 914 ALB 008 europe | 915 GEO 268 meca
916 KAZ 398 meca | 917 KGZ 417 meca | 918 BGR 100 europe | 921 MDA 498 europe | 922 RUS 643 europe
923 TJK 762 meca | 924 CHN 156 asia | 925 TKM 795 meca | 926 UKR 804 europe | 927 UZB 860 meca
935 CZE 203 adv | 936 SVK 703 adv | 939 EST 233 adv | 941 LVA 428 adv | 942 SRB 688 europe
943 MNE 499 europe | 944 HUN 348 europe | 946 LTU 440 adv | 948 MNG 496 asia | 960 HRV 191 adv
961 SVN 705 adv | 962 MKD 807 europe | 963 BIH 070 europe | 964 POL 616 europe | 967 XKX - europe
968 ROU 642 europe
"""

# The WEO's own aggregates, kept as forecast series but never on the map.
AGGREGATES = {1: "WLD", 110: "ADV", 163: "EUR", 200: "EMDE"}


def table() -> pl.DataFrame:
    """``ifs, iso3, iso_num, group`` for every country (aggregates have group ``agg``)."""
    rows = []
    for entry in _TABLE.replace("\n", "|").split("|"):
        if entry.strip():
            ifs, iso3, num, group = entry.split()
            rows.append((int(ifs), iso3, None if num == "-" else num, group))
    rows += [(ifs, code, None, "agg") for ifs, code in AGGREGATES.items()]
    return pl.DataFrame(rows, schema={"ifs": pl.Int32, "iso3": pl.Utf8, "iso_num": pl.Utf8, "group": pl.Utf8}, orient="row")
