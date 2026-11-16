# Alsó bölcsességfogak műtéti eltávolítása – animált, feliratozott oktatóvideó

Sémás, oktatási célú animáció a tankönyv 6.1 fejezetének leírása alapján
(lebenyképzés, csonteltávolítás, disszekció, a verticalis helyzetű fog eltávolítása, sebzárás).

## Fájlok

| Fájl | Tartalom |
|---|---|
| `out/bolcsessegfog_mutet.mp4` | A kész videó (1920×1080, 25 fps, beégetett magyar felirat + kapcsolható felirat-sáv) |
| `out/bolcsessegfog_mutet.hu.srt` | A felirat külön SRT fájlban (pl. lejátszóba, YouTube-ra) |
| `out/fejezetek.txt` | Fejezet-időbélyegek |
| `animation.html` | Az animáció forrása (böngészőben megnyitva valós időben lejátszható; `#t=120` a 120. másodperctől indít) |
| `render.js` | Képkockánkénti renderelés Playwright + ffmpeg segítségével |

## Újrarenderelés

```bash
cd video
node render.js video        # out/bolcsessegfog_mutet.mp4 + .srt
node render.js preview 30 95 # egyes képkockák PNG-ben ellenőrzéshez
```

A szövegek (feliratok, kulcspontok) az `animation.html` `scene({...})` blokkjaiban a `caps` és `bullets` mezőkben szerkeszthetők;
a feliratok időzítése a szöveg hosszából automatikusan számolódik.

## Jelenetek

1. Cím
2. 6.1.1 Lebenyképzés – alapelvek (teljes vastagságú mucoperiostealis lebeny, követelmények)
3. 6.1.1 Segédmetszés nélküli („envelope”) lebeny metszésvonala
4. 6.1.1 A lebeny leválasztása, a n. lingualis lefutása
5. 6.1.1 Az envelope lebeny előnyei és hátrányai
6. 6.1.1 Segédmetszéssel készített lebeny (45°, max. 15–20 mm)
7. 6.1.2 Csonteltávolítás – eszközök
8. 6.1.2 Mély impactio – perforációs technika
9. 6.1.2 A korona felszabadítása a zománc-cement határig
10. 6.1.3 A fog disszekciója
11. 6.1.3 A korona átvágása (4/5 fúró + véső), a n. lingualis védelme
12. 6.1.4 Verticalis helyzetű fog
13. 6.1.4 Kúpos gyökerek – Barry-féle emelő
14. 6.1.4 Distalisan hajlott gyökerek – Lecluse-emelő (6.9. ábra)
15. 6.1.4 Különálló gyökerek
16. 6.1.8 Sebrevízió, fogzacskó-maradvány
17. 6.1.8 Öltéstechnika (papilla csomós öltés, distalis matracöltés)
18. Összefoglalás

> Az ábrák sematikusak, nem méretarányosak; a videó a tankönyvi szöveg kiegészítésére szolgál, nem helyettesíti azt.
