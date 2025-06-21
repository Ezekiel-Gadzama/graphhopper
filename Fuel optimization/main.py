import json
from datetime import timedelta
from services.optimization import FuelOptimizer
from services.graphhopper import GraphHopper
from utils.visualization import visualize_route
from config.settings import settings

def main():
    # Define OSM IDs to process
    unique_osm_ids = [
        498126573, 498126585, 498126586, 498126562,
        240294599, 761483024, 46737021, 240294607
    ]

    # Initialize and run optimization
    optimizer = FuelOptimizer()
    
    # Update custom model with all OSM IDs at once (more efficient)
    optimizer.update_custom_model(unique_osm_ids)

    # Request route from GraphHopper
    start = (55.761368, 37.537752)  # Latitude, Longitude
    end = (55.669699, 37.626329)
    
    # Load the custom model that was just updated
    with open(settings.CUSTOM_MODEL_PATH) as f:
        custom_model = json.load(f)
    
    # Get optimized route
    graphhopper = GraphHopper(base_url=settings.GRAPHHOPPER_URL)
    route = graphhopper.request_route(
        start_coord=start,
        end_coord=end,
        custom_model=custom_model
    )

    # Process and display results
    if route and "paths" in route:
        print("\nRoute processing complete")
        print(f"Total distance: {route['paths'][0]['distance']/1000:.2f} km")
        print(f"Estimated time: {timedelta(seconds=route['paths'][0]['time']/1000)}")
        
        # Print important edges in the route
        print("\nKey road segments in route:")
        for i, edge in enumerate(route["paths"][0].get("details", {}).get("osm_id", [])[:5]):  # Show first 5
            print(f"Segment {i+1}: OSM ID {edge[2]} positions {edge[0]}-{edge[1]}")

    # Visualize the route
    visualize_route(
        start_point=start,
        route_data=route,
        custom_model=custom_model
    )

if __name__ == "__main__":
    main()

# import re

# def decode_polyline_custom(encoded, format="ffii", precision=6):
#     if not encoded:
#         return []

#     if encoded[0].isdigit() or encoded[0] == '-':
#         # Old style decoding
#         parts = re.split(r':|;', encoded)
#         parts = list(map(float, parts))  # or int if appropriate
#         return [parts[i:i+len(format)] for i in range(0, len(parts), len(format))]

#     index = 0
#     latlng = []
#     shift = 0
#     result = 0
#     byte = None
#     prev = [0] * len(format)
#     output = []
#     while index < len(encoded):
#         for i in range(len(format)):
#             shift = 0
#             result = 0
#             while True:
#                 byte = ord(encoded[index]) - 63
#                 index += 1
#                 result |= (byte & 0x1F) << shift
#                 shift += 5
#                 if byte < 0x20:
#                     break
#             diff = ~(result >> 1) if (result & 1) else (result >> 1)
#             prev[i] += diff
#             if format[i] == 'f':
#                 latlng.append(prev[i] / (10 ** precision))
#             else:
#                 latlng.append(prev[i])
#         output.append(latlng)
#         latlng = []
#     return output
# polyline_str = r"{~r|fgB_uwico@iD_zuEwDo_eDkA_pRkA_af@u@_pRw@_pRoGowH{nC_pRe@_t`BM_af@]o{vAG_pRSojcA{@_ibEG_pRU_af@qa@o~w~GM_kiFg@od_QIo}}BC_ry@GoljBO_zuEU_kiFC_af@Coh\C_af@Eoyo@C_af@C_af@C_af@Coh\C_af@C_af@C_af@Coh\Coyo@A_pRCoyo@Eo{vAwA_eg}@sAond~@sA_gn~@O_seKsAond~@m@_hxa@sA_gn~@sA_gn~@sAond~@sA_gn~@sA_gn~@uA_vz}@o\odpuSiBo}p}@sAond~@uA_eg}@wAond~@cA_uns@WourQSoo}MIocsFOoz{JO_seKqA_vz}@sAo}p}@uAo_x~@o@obic@EonqCsAo}p}@Yod_Q[_n|QQ_dyKwAond~@uAo}p}@mZoxcgRu@oh~f@qAo{i|@sAond~@sA_gn~@sA_gn~@wA_vz}@]ojtTcA_sgr@G_ibEWod_QIocsFC_t`BGopxDEonqCC_t`BG_ibEEonqCEonqC]_tqUU_jnOqAol}|@c@_kzYQ_ulLK_~cHQomvLKoezGQomvLM_`kIK_~cHQomvLOoz{J{@_idl@sA_gn~@_@onbWS_hgNU_jnO[oy`TyV_i~gPC_af@GojcACoh\C_af@C_af@Coh\E_ry@Coh\C_af@Coh\C_af@C_af@C_af@C_af@E_cmAIo}}BKopxDW_yzNa@_isXsA_gn~@s@owjf@IocsFKoezGQomvL[_awSG_ibEE_vgCG_xnDE_vgCcB_vz}@_B_vz}@s@_seKC_pRC_pRCoh\Coh\qAok`_@[_kiFGoh\qA_rjT_@_etBe@or_FQ_ry@M_pRKowHa@oh\Ioyo@G_af@_@_ry@Goh\u@_brJGoh\Y_xnDCoh\Coh\C_af@yBo{i|@a@_n|QC_ry@Coyo@E_ry@i@oihJEoh\E_pREoh\}Boh\qNorkpFA_af@M_mpGA_af@IopxDC_cmASoxtII_g{CAoh\A_af@Aoh\A_af@Aoh\CojcAGonqCC_cmAIoalESo|bLO_owHCojcAC_ry@K_vgCU_xnD_@_`kIGo}}BE_t`BKor_FW_wsMG_g{Co@_bc^KotfGQo|bLc@ol{UAoh\CojcACojcAO_mpGC_ry@Aoh\A_af@C_ry@SoihJG_g{CeAo}_j@Q_xnDEoh\C_pRC_pRCoh\W_||FGoljBm@onbWEoljBSogaIG_etB{@_||FGoh\E_pRE_af@uBoijq@K_ibEIo_eDKoalEOotfG_@_luPK_zuEM_zuECoyo@Coyo@QoalEC_af@k@_q~IEoyo@e@opxDa@_||FCoh\C_pRQ_cmAGoh\O_pRsoTojtTM_pRGowHce@oh\g@_af@Woh\eA_af@c{Foh\cC_vgCaB_pRWowHmAoh\}A_af@WowHeH_af@yBowHahM_pRuD_cmAw\ozzoHIopxDCojcAAoh\A_af@A_af@Aoh\QovmHCojcAE_t`BK_ibEq@oek[G_g{CK_kiFu@o~z`@C_cmA[_jnOEoljBE_t`Bg@_jnOQor_FEo{vAEo{vAq_A_l``Ps@_pRS_pRk@owHKoh\GowHGowHGoh\Koh\I_pRI_pRK_pRIoh\i@owH{@_pRSowHOowH}N_ry@_AowH}F?"
# points = decode_polyline_custom(polyline_str, format="ffii", precision=6)
# print(points[:5])  # Show first 5 decoded points
