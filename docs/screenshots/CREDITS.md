# Screenshot credits

Every screenshot in this folder shows a demo library, not a real one. No real Immich server,
household, or Claude account was involved.

## How the demo was made

- The app ran on a local port with a throwaway data folder. Immich was the in-memory
  `FakeImmich` from `src/highlights/immich.py`, filled with about 2,500 invented assets: five
  trips and twelve months, with made-up dates, places and file sizes.
- The real pipeline code did the work: `scan` found the trips and months, `pick` built the
  contact sheets, `render` cut the Iceland and Norway videos with ffmpeg on the CPU, and
  `cleanup` ran against the fake. A few states were written straight to the database: the
  August render in progress, the finished December video and the skipped January.
- **Claude was not called.** A stub picker returned canned picks, so nothing was sent to
  Anthropic. The picks in the screenshots are not real Claude output.
- The demo "video clips" are slow pans across still photos, generated with ffmpeg.
- `contact-sheets.png` is one video sheet stacked on one photo sheet, exactly as `media.py`
  made them (scaled down). It shows the kind of image Claude would be sent.
- Captured with headless Chromium at 1440x900 and 390x844, device scale factor 2, dark scheme,
  then reduced to 256-color PNGs to keep the files small.

## Photos

All photos are from [Wikimedia Commons](https://commons.wikimedia.org) and are released under
[CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) (public domain dedication), as
stated on each file page when they were downloaded on 2026-11-14. CC0 does not require credit;
the authors are listed anyway, with thanks. The photos stand in for invented trips and were not
taken where the demo labels say.

| Photo | Author |
|---|---|
| [2014.06.21.115338 Cat window Herrenstraße Münstermaifeld.jpg](https://commons.wikimedia.org/wiki/File:2014.06.21.115338_Cat_window_Herrenstra%C3%9Fe_M%C3%BCnstermaifeld.jpg) | Hermann Luyken |
| [500px photo (249193545).jpeg](https://commons.wikimedia.org/wiki/File:500px_photo_(249193545).jpeg) | Максим Андреев |
| [A beautiful road with leaves falling.jpg](https://commons.wikimedia.org/wiki/File:A_beautiful_road_with_leaves_falling.jpg) | Valiphotos |
| [American Breakfast - Snais's Cafe 2026-01-05.jpg](https://commons.wikimedia.org/wiki/File:American_Breakfast_-_Snais%27s_Cafe_2026-01-05.jpg) | Andy Li |
| [An Alpine Landscape NZ.jpg](https://commons.wikimedia.org/wiki/File:An_Alpine_Landscape_NZ.jpg) | Bernard Spragg. NZ from Christchurch, New Zealand |
| [Apple Orchards with a view of Canterbury Cathedral.jpg](https://commons.wikimedia.org/wiki/File:Apple_Orchards_with_a_view_of_Canterbury_Cathedral.jpg) | Digihum |
| [Apples in the Wincheap Orchard.jpg](https://commons.wikimedia.org/wiki/File:Apples_in_the_Wincheap_Orchard.jpg) | Digihum |
| [Autumn Calgary Alberta (15) (8168770359).jpg](https://commons.wikimedia.org/wiki/File:Autumn_Calgary_Alberta_(15)_(8168770359).jpg) | Bernard Spragg. NZ from Christchurch, New Zealand |
| [Autumn Calgary Alberta. (8168771277).jpg](https://commons.wikimedia.org/wiki/File:Autumn_Calgary_Alberta._(8168771277).jpg) | Bernard Spragg. NZ from Christchurch, New Zealand |
| [Autumn Calgary Alberta. (8168795388).jpg](https://commons.wikimedia.org/wiki/File:Autumn_Calgary_Alberta._(8168795388).jpg) | Bernard Spragg. NZ from Christchurch, New Zealand |
| [Autumn Calgary, Alberta; October 2007 (2).jpg](https://commons.wikimedia.org/wiki/File:Autumn_Calgary,_Alberta;_October_2007_(2).jpg) | Bernard Spragg. NZ |
| [Autumn path.jpg](https://commons.wikimedia.org/wiki/File:Autumn_path.jpg) | Simon Svensson Thunman |
| [Bear Mountain Trail No. 54 (35132080921).jpg](https://commons.wikimedia.org/wiki/File:Bear_Mountain_Trail_No._54_(35132080921).jpg) | Coconino National Forest |
| [Bermuda (UK) image number 106 sandcastle Horseshoe Bay beach spires ocean clouds.jpg](https://commons.wikimedia.org/wiki/File:Bermuda_(UK)_image_number_106_sandcastle_Horseshoe_Bay_beach_spires_ocean_clouds.jpg) | Tomwsulcer |
| [Bermuda (UK) photos number 65 sandcastle clouds beach Atlantic Ocean.jpg](https://commons.wikimedia.org/wiki/File:Bermuda_(UK)_photos_number_65_sandcastle_clouds_beach_Atlantic_Ocean.jpg) | Tomwsulcer |
| [Berufjörður (East-Iceland) - Roland Larsson 2017-05-28 (Unsplash SCjhLOM 4ks).jpg](https://commons.wikimedia.org/wiki/File:Berufj%C3%B6r%C3%B0ur_(East-Iceland)_-_Roland_Larsson_2017-05-28_(Unsplash_SCjhLOM_4ks).jpg) | Roland Larsson becomingsilence |
| [Beverly Beach, Oregon (36362093605).jpg](https://commons.wikimedia.org/wiki/File:Beverly_Beach,_Oregon_(36362093605).jpg) | icetsarina from United States |
| [Bicycle path in the town park "Nowe Bulwary" in Tomaszów Mazowiecki, Poland.jpg](https://commons.wikimedia.org/wiki/File:Bicycle_path_in_the_town_park_%22Nowe_Bulwary%22_in_Tomasz%C3%B3w_Mazowiecki,_Poland.jpg) | WrS.tm.pl |
| [Big Sunflower waiting for a Visitor.jpg](https://commons.wikimedia.org/wiki/File:Big_Sunflower_waiting_for_a_Visitor.jpg) | HLI-Photography |
| [Bishamondo and Daigo-ji, Kyoto - Bishamondo7329.jpg](https://commons.wikimedia.org/wiki/File:Bishamondo_and_Daigo-ji,_Kyoto_-_Bishamondo7329.jpg) | lumoplank |
| [Black Sand Beach (39040413804).jpg](https://commons.wikimedia.org/wiki/File:Black_Sand_Beach_(39040413804).jpg) | Sean O Riordan |
| [Black Sand Beach, Iceland (Unsplash HPWmp 52caE).jpg](https://commons.wikimedia.org/wiki/File:Black_Sand_Beach,_Iceland_(Unsplash_HPWmp_52caE).jpg) | Tim Trad timtrad |
| [Bleached driftwood tree below the bluff, Agate Beach, Sue-meg State Park, California.jpg](https://commons.wikimedia.org/wiki/File:Bleached_driftwood_tree_below_the_bluff,_Agate_Beach,_Sue-meg_State_Park,_California.jpg) | Z3lvs |
| [Bodine Mountain Road (27709310311).jpg](https://commons.wikimedia.org/wiki/File:Bodine_Mountain_Road_(27709310311).jpg) | Nicholas A. Tonelli from Northeast Pennsylvania, USA |
| [Burnie-Farmers-Market-Veges-20150207-011.jpg](https://commons.wikimedia.org/wiki/File:Burnie-Farmers-Market-Veges-20150207-011.jpg) | Gary Houston |
| [Campfire Cooking (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:Campfire_Cooking_(Unsplash).jpg) | Evan Kirby evankirby2 |
| [Camping in the mountains (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:Camping_in_the_mountains_(Unsplash).jpg) | Christopher Jolly chris_jolly |
| [Carters Beach Driftwood Shelter.jpg](https://commons.wikimedia.org/wiki/File:Carters_Beach_Driftwood_Shelter.jpg) | Carters27 |
| [Cat napping by the window (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:Cat_napping_by_the_window_(Unsplash).jpg) | Yanko Peyankov peyankov |
| [Chelyabinsk meteorite (garden tomato).jpg](https://commons.wikimedia.org/wiki/File:Chelyabinsk_meteorite_(garden_tomato).jpg) | Georg Pik |
| [Collection of strawberry (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:Collection_of_strawberry_(Unsplash).jpg) | veeterzy veeterzy |
| [Croghan Mountain as seen from a road to the NE of the mountain 01.jpg](https://commons.wikimedia.org/wiki/File:Croghan_Mountain_as_seen_from_a_road_to_the_NE_of_the_mountain_01.jpg) | Ridiculopathy |
| [Driftwood at the sand beach (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:Driftwood_at_the_sand_beach_(Unsplash).jpg) | Mitchell Schwartz mitsch |
| [Driftwood shore.jpg](https://commons.wikimedia.org/wiki/File:Driftwood_shore.jpg) | San906 |
| [Driftwood(byPJrvs).jpg](https://commons.wikimedia.org/wiki/File:Driftwood(byPJrvs).jpg) | Paul Jarvis |
| [Driftwood, Ocean Beach, January 2023.jpg](https://commons.wikimedia.org/wiki/File:Driftwood,_Ocean_Beach,_January_2023.jpg) | Nvss132 |
| [Driving off-road along the cold coast (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:Driving_off-road_along_the_cold_coast_(Unsplash).jpg) | Tim Trad timtrad |
| [Elk in Meadow, Cataloochee, NC (31780399217).jpg](https://commons.wikimedia.org/wiki/File:Elk_in_Meadow,_Cataloochee,_NC_(31780399217).jpg) | Warren LeMay from Cincinnati, OH, United States |
| [Elk in Meadow, Cataloochee, NC (31780399917).jpg](https://commons.wikimedia.org/wiki/File:Elk_in_Meadow,_Cataloochee,_NC_(31780399917).jpg) | Warren LeMay from Cincinnati, OH, United States |
| [Elk in Meadow, Cataloochee, NC (32846789968).jpg](https://commons.wikimedia.org/wiki/File:Elk_in_Meadow,_Cataloochee,_NC_(32846789968).jpg) | Warren LeMay from Cincinnati, OH, United States |
| [Elk in Meadow, Cataloochee, NC (32846884728).jpg](https://commons.wikimedia.org/wiki/File:Elk_in_Meadow,_Cataloochee,_NC_(32846884728).jpg) | Warren LeMay from Cincinnati, OH, United States |
| [Elk in Meadow, Cataloochee, NC (46721750741).jpg](https://commons.wikimedia.org/wiki/File:Elk_in_Meadow,_Cataloochee,_NC_(46721750741).jpg) | Warren LeMay from Cincinnati, OH, United States |
| [Elk Meadow Lodge & RV Resort around sundown, Estes Park, 2009.jpg](https://commons.wikimedia.org/wiki/File:Elk_Meadow_Lodge_%26_RV_Resort_around_sundown,_Estes_Park,_2009.jpg) | DimiTalen |
| [Evening Lake Pukaki.NZ. (10339369126).jpg](https://commons.wikimedia.org/wiki/File:Evening_Lake_Pukaki.NZ._(10339369126).jpg) | Bernard Spragg. NZ from Christchurch, New Zealand |
| [Felix Plakolb 2016 (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:Felix_Plakolb_2016_(Unsplash).jpg) | Felix Plakolb felix_plakolb |
| [Fire and logs at night (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:Fire_and_logs_at_night_(Unsplash).jpg) | Sandis Helvigs sandishelvigs |
| [Freedom Icelandic Landscape (135237371).jpeg](https://commons.wikimedia.org/wiki/File:Freedom_Icelandic_Landscape_(135237371).jpeg) | Emanuele Rossini |
| [Garden fresh tomatoes (20281911391).jpg](https://commons.wikimedia.org/wiki/File:Garden_fresh_tomatoes_(20281911391).jpg) | terri_bateman |
| [Golden retriever alert (30190754125).jpg](https://commons.wikimedia.org/wiki/File:Golden_retriever_alert_(30190754125).jpg) | David Whelan |
| [Golden-retriever-1827903 1920.jpg](https://commons.wikimedia.org/wiki/File:Golden-retriever-1827903_1920.jpg) | RetyiRetyi |
| [Golden-retriever-dog.jpg](https://commons.wikimedia.org/wiki/File:Golden-retriever-dog.jpg) | Karen Arnold |
| [Goleudau Gogledd Northern Lights Ffair Rhos.jpg](https://commons.wikimedia.org/wiki/File:Goleudau_Gogledd_Northern_Lights_Ffair_Rhos.jpg) | WillowHelyg |
| [Gongga Snow Mountain Cloud On Foot Mountaineer.jpg](https://commons.wikimedia.org/wiki/File:Gongga_Snow_Mountain_Cloud_On_Foot_Mountaineer.jpg) | yongxinz |
| [Grassy foredune above the beach on the Oregon coast between Winchester Bay and Bandon.jpg](https://commons.wikimedia.org/wiki/File:Grassy_foredune_above_the_beach_on_the_Oregon_coast_between_Winchester_Bay_and_Bandon.jpg) | Z3lvs |
| [Grazing horses in Iceland (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:Grazing_horses_in_Iceland_(Unsplash).jpg) | Isabella Jusková bellaskova |
| [Green northern lights (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:Green_northern_lights_(Unsplash).jpg) | HyunKuk Kim spacekhk |
| [Green tent on a snow covered mountain (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:Green_tent_on_a_snow_covered_mountain_(Unsplash).jpg) | Sam X samx |
| [High Tunnel at Pumpkin Patch - 52450219217.jpg](https://commons.wikimedia.org/wiki/File:High_Tunnel_at_Pumpkin_Patch_-_52450219217.jpg) | Alabama Extension |
| [Horse in a snowy field in close-up (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:Horse_in_a_snowy_field_in_close-up_(Unsplash).jpg) | Benny Jackson themightymerlin |
| [Horses nuzzling on a cold morning (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:Horses_nuzzling_on_a_cold_morning_(Unsplash).jpg) | Anders Jildén andersjilden |
| [Iceland July.jpg](https://commons.wikimedia.org/wiki/File:Iceland_July.jpg) | Snyder261 |
| [Icland nature 3.jpg](https://commons.wikimedia.org/wiki/File:Icland_nature_3.jpg) | Snyder261 |
| [Idyllic landscape with a waterfall (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:Idyllic_landscape_with_a_waterfall_(Unsplash).jpg) | Robert Lukeman robertlukeman |
| [Kayaks and canoes on a lake (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:Kayaks_and_canoes_on_a_lake_(Unsplash).jpg) | Matt Thomason shipmate |
| [Kitty cat in a window sill perch.jpg](https://commons.wikimedia.org/wiki/File:Kitty_cat_in_a_window_sill_perch.jpg) | Tomwsulcer |
| [Kálfafell, Iceland (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:K%C3%A1lfafell,_Iceland_(Unsplash).jpg) | Gian-Reto Tarnutzer reto_gian |
| [Lake Louise. Banff National Park. (8168779820).jpg](https://commons.wikimedia.org/wiki/File:Lake_Louise._Banff_National_Park._(8168779820).jpg) | Bernard Spragg. NZ from Christchurch, New Zealand |
| [Lofoten, Norway (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:Lofoten,_Norway_(Unsplash).jpg) | Johannes Groll followhansi |
| [Log cabin, Elk Meadow Lodge & RV Resort, Estes Park, 2009.jpg](https://commons.wikimedia.org/wiki/File:Log_cabin,_Elk_Meadow_Lodge_%26_RV_Resort,_Estes_Park,_2009.jpg) | DimiTalen |
| [Malbach valley, path dividing, Ehrenbach.jpg](https://commons.wikimedia.org/wiki/File:Malbach_valley,_path_dividing,_Ehrenbach.jpg) | Gerda Arendt |
| [Moscow, tiny snowman, Jan 2026 04.jpg](https://commons.wikimedia.org/wiki/File:Moscow,_tiny_snowman,_Jan_2026_04.jpg) | Retired electrician |
| [Moscow, tiny snowman, Jan 2026 05.jpg](https://commons.wikimedia.org/wiki/File:Moscow,_tiny_snowman,_Jan_2026_05.jpg) | Retired electrician |
| [Mountain Road in Iceland.jpg](https://commons.wikimedia.org/wiki/File:Mountain_Road_in_Iceland.jpg) | Jonatan Pie |
| [Nieder-OIm Marktplatz während der Blauen Stunde.jpg](https://commons.wikimedia.org/wiki/File:Nieder-OIm_Marktplatz_w%C3%A4hrend_der_Blauen_Stunde.jpg) | ManuelB701 |
| [Northern Lights at Lauklines Norway.jpg](https://commons.wikimedia.org/wiki/File:Northern_Lights_at_Lauklines_Norway.jpg) | Sebastian Kowalski |
| [Organic apple orchard in Ressen (Lingewaard).jpg](https://commons.wikimedia.org/wiki/File:Organic_apple_orchard_in_Ressen_(Lingewaard).jpg) | Lendskaip |
| [Palomino horses by a waterfall (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:Palomino_horses_by_a_waterfall_(Unsplash).jpg) | Sergi Ferrete sergiferrete |
| [Pike Place Farmers Market Express June 25 (9137379922).jpg](https://commons.wikimedia.org/wiki/File:Pike_Place_Farmers_Market_Express_June_25_(9137379922).jpg) | Seattle City Council from Seattle |
| [Pine Mountain Road Pine Mountain.jpg](https://commons.wikimedia.org/wiki/File:Pine_Mountain_Road_Pine_Mountain.jpg) | Shiftchange |
| [Pumpkins with patches (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:Pumpkins_with_patches_(Unsplash).jpg) | sydney zentz srz |
| [Reykjafoss Waterfall, Iceland 01.jpg](https://commons.wikimedia.org/wiki/File:Reykjafoss_Waterfall,_Iceland_01.jpg) | Netha Hussain |
| [Reykjafoss Waterfall, Iceland 03.jpg](https://commons.wikimedia.org/wiki/File:Reykjafoss_Waterfall,_Iceland_03.jpg) | Netha Hussain |
| [Reykjafoss Waterfall, Iceland 08.jpg](https://commons.wikimedia.org/wiki/File:Reykjafoss_Waterfall,_Iceland_08.jpg) | Netha Hussain |
| [Reykjafoss Waterfall, Iceland 12.jpg](https://commons.wikimedia.org/wiki/File:Reykjafoss_Waterfall,_Iceland_12.jpg) | Netha Hussain |
| [Reynisfjara Black Sand Beach, Iceland (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:Reynisfjara_Black_Sand_Beach,_Iceland_(Unsplash).jpg) | Rucksack Magazine rucksackmag |
| [Rock on black sand beach (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:Rock_on_black_sand_beach_(Unsplash).jpg) | Courtney Read readintoit |
| [Sandcastle on the beach of Ahlbeck.JPG](https://commons.wikimedia.org/wiki/File:Sandcastle_on_the_beach_of_Ahlbeck.JPG) | Dinkum |
| [Short-Beach-Oregon.JPG](https://commons.wikimedia.org/wiki/File:Short-Beach-Oregon.JPG) | Goodwid |
| [Simpson Beach Coos Bay Oregon (187150565).jpeg](https://commons.wikimedia.org/wiki/File:Simpson_Beach_Coos_Bay_Oregon_(187150565).jpeg) | Justen |
| [Slate Mountain Trail (36093604264).jpg](https://commons.wikimedia.org/wiki/File:Slate_Mountain_Trail_(36093604264).jpg) | Coconino National Forest |
| [Slate Mountain Trail (36094141714).jpg](https://commons.wikimedia.org/wiki/File:Slate_Mountain_Trail_(36094141714).jpg) | Coconino National Forest |
| [Slate Mountain Trail (36756828622).jpg](https://commons.wikimedia.org/wiki/File:Slate_Mountain_Trail_(36756828622).jpg) | Coconino National Forest |
| [Slate Mountain Trail (36756900292).jpg](https://commons.wikimedia.org/wiki/File:Slate_Mountain_Trail_(36756900292).jpg) | Coconino National Forest |
| [Snowman on a foggy day.jpg](https://commons.wikimedia.org/wiki/File:Snowman_on_a_foggy_day.jpg) | Terry.grignon |
| [Spectacular Northern Lights at -50°C in Pinehouse Lake, Saskatchewan, Canada.jpg](https://commons.wikimedia.org/wiki/File:Spectacular_Northern_Lights_at_-50%C2%B0C_in_Pinehouse_Lake,_Saskatchewan,_Canada.jpg) | Dre Erwin Photo |
| [Spring. Lake Tekapo. NZ. (49962004662).jpg](https://commons.wikimedia.org/wiki/File:Spring._Lake_Tekapo._NZ._(49962004662).jpg) | Bernard Spragg. NZ from Christchurch, New Zealand |
| [Strawberries at a Farmers Market.jpg](https://commons.wikimedia.org/wiki/File:Strawberries_at_a_Farmers_Market.jpg) | Alabama Extension |
| [Sunflower field in late afternoon sun with cloudy sky in Munich, Germany.jpg](https://commons.wikimedia.org/wiki/File:Sunflower_field_in_late_afternoon_sun_with_cloudy_sky_in_Munich,_Germany.jpg) | Pittigrilli |
| [Sunflower Fields.jpg](https://commons.wikimedia.org/wiki/File:Sunflower_Fields.jpg) | Wenchieh Yang |
| [Surf-lined beach below a forested bluff curving toward Port Orford, Oregon.jpg](https://commons.wikimedia.org/wiki/File:Surf-lined_beach_below_a_forested_bluff_curving_toward_Port_Orford,_Oregon.jpg) | Z3lvs |
| [Tateyama Kurobe Alpine Route - AlpineRoute6309.jpg](https://commons.wikimedia.org/wiki/File:Tateyama_Kurobe_Alpine_Route_-_AlpineRoute6309.jpg) | lumoplank |
| [Tateyama Kurobe Alpine Route - AlpineRoute6313.jpg](https://commons.wikimedia.org/wiki/File:Tateyama_Kurobe_Alpine_Route_-_AlpineRoute6313.jpg) | lumoplank |
| [The American Breakfast - The Orchard Cafe 2025-12-04.jpg](https://commons.wikimedia.org/wiki/File:The_American_Breakfast_-_The_Orchard_Cafe_2025-12-04.jpg) | Andy Li |
| [The Black Sand Beach (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:The_Black_Sand_Beach_(Unsplash).jpg) | Tim Trad timtrad |
| [The Golden Retriever Ringo on November 27, 2019.jpg](https://commons.wikimedia.org/wiki/File:The_Golden_Retriever_Ringo_on_November_27,_2019.jpg) | George E. Koronaios |
| [The Northern Lights Cathedral.jpg](https://commons.wikimedia.org/wiki/File:The_Northern_Lights_Cathedral.jpg) | Stch2022 |
| [This primitive campground and day use area offers a scenic view of the San Francisco Peaks in the cool aspen trees that surround Lockett Meadow. This is a terrific campground for those who cherish a (21707508140).jpg](https://commons.wikimedia.org/wiki/File:This_primitive_campground_and_day_use_area_offers_a_scenic_view_of_the_San_Francisco_Peaks_in_the_cool_aspen_trees_that_surround_Lockett_Meadow._This_is_a_terrific_campground_for_those_who_cherish_a_(21707508140).jpg) | Coconino National Forest |
| [Three graceful horses (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:Three_graceful_horses_(Unsplash).jpg) | Fabian Burghardt fabuchao |
| [Tomato crop at Mountain Horticultural Crops Research Station.jpg](https://commons.wikimedia.org/wiki/File:Tomato_crop_at_Mountain_Horticultural_Crops_Research_Station.jpg) | Indy beetle |
| [Tomato plants growing in garbage barrels alongside house.JPG](https://commons.wikimedia.org/wiki/File:Tomato_plants_growing_in_garbage_barrels_alongside_house.JPG) | Tomwsulcer |
| [Tomatoes for sale.jpg](https://commons.wikimedia.org/wiki/File:Tomatoes_for_sale.jpg) | Jeffery Martin |
| [Waves crashing on rocky coast at Heceta Beach (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:Waves_crashing_on_rocky_coast_at_Heceta_Beach_(Unsplash).jpg) | Nathan Anderson nathananderson |
| [White horse in Iceland (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:White_horse_in_Iceland_(Unsplash).jpg) | Melissa Regina tadmint |
| [Winter Waves (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:Winter_Waves_(Unsplash).jpg) | Tim Trad timtrad |
| [Wollongong Breakwater Lighthouse (21351551761).jpg](https://commons.wikimedia.org/wiki/File:Wollongong_Breakwater_Lighthouse_(21351551761).jpg) | Bernard Spragg. NZ from Christchurch, New Zealand |
| [Yellow Aspen trees in Fall.jpg](https://commons.wikimedia.org/wiki/File:Yellow_Aspen_trees_in_Fall.jpg) | Mshuang2 |
| [Yellow Halloween pumpkins (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:Yellow_Halloween_pumpkins_(Unsplash).jpg) | John Silliman john_silliman |
