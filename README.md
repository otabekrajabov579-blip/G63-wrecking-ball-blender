# Kran shari Mercedes-Benz G63 ga tushishi — Blender 5.2 fizik simulyatsiyasi

**2-mustaqil ish** · «Realistik vizual effektlar va simulyatsia» fani
**Mavzu:** Zarralar va obyektlar to‘qnashuvini modellashtirish hamda to‘qnashuvdan keyingi harakat parametrlarini aniqlash
**Bajardi:** Rajabov Otabek, 241-23 guruh · **Tekshirdi:** Jo‘rayev Azizbek · TATU, 2026

## Fayllar
| Fayl | Tavsif |
|---|---|
| `G63_WreckingBall.blend` | Asosiy loyiha fayli (Blender 5.2, ~188 MB). Barcha teksturalar, HDRI va ovoz fayl ichiga joylangan, Rigid Body simulyatsiyasi bake qilingan. |
| `scripts/` | Sahnani avtomatik yig‘uvchi, o‘lchov va tajriba Python skriptlari |
| `CREDITS.txt` | Foydalanilgan modellar, teksturalar va ovozlar mualliflari va litsenziyalari |

## Ochish
1. Blender **5.2** (yoki undan yangi) bilan `G63_WreckingBall.blend` ni oching.
2. Animatsiya: 648 kadr, 24 kadr/s (27 soniya). Zarba 291-kadrda.
3. Render: EEVEE, 1920×1080, `Render → Render Animation`.

## Simulyatsiya
- 1000 kg li shar 25 m balandlikdan tushadi (zarbagacha tezlik ≈ 21 m/s).
- 9 ta oyna Voronoi usulida 623 ta Rigid Body bo‘lakka, 6500 ta mayda zarrachaga bo‘linadi.
- Metall korpus Geometry Nodes yordamida zarba kuchiga mos bukiladi, 11 ta qism uzilib uchadi.

Model: «Mersedes-Benz G63 AMG» – Black Snow (Sketchfab), CC BY 4.0. Batafsil: `CREDITS.txt`.
