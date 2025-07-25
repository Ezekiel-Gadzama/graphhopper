package com.graphhopper.routing.weighting.custom;

import com.graphhopper.routing.ev.*;
import com.graphhopper.util.EdgeIteratorState;
import com.graphhopper.util.JsonFeature;
import com.graphhopper.util.CustomModel;
import java.util.Map;
import org.locationtech.jts.geom.Polygon;
import org.locationtech.jts.geom.Polygonal;
import org.locationtech.jts.geom.prep.PreparedPolygon;


public class CustomWeightingHelper_${modelHash?replace(",","")} extends CustomWeightingHelper {
    <#list variables as var>
        <#if var.isArea>
            private Polygon ${var.name};
        <#else>
            <#if var.name == "road_class">
                private EnumEncodedValue<RoadClass> ${var.name}_enc;
            <#else>
                private ${var.type} ${var.name}_enc;
            </#if>
        </#if>
    </#list>

    @Override
    public void init(CustomModel customModel, EncodedValueLookup lookup, Map<String, JsonFeature> areas) {
        super.init(customModel, lookup, areas);
        <#list variables as var>
            <#if var.isArea>
                this.${var.name} = createAreaPolygon("${var.name?replace("in_", "")}", areas);
            <#else>
                <#if var.name == "road_class">
                    this.${var.name}_enc = lookup.getEncodedValue("${var.name}", EnumEncodedValue.class);
                <#else>
                    this.${var.name}_enc = lookup.getEncodedValue("${var.name}", ${var.type}.class);
                </#if>
            </#if>
        </#list>
    }

    @Override
    public double getPriority(EdgeIteratorState edge, boolean reverse) {
        // Add variable declarations
        <#list variables as var>
            <#if !var.isArea && var.name != "osm_id">
                <#if var.name == "road_class">
                    RoadClass ${var.name} = edge.get(${var.name}_enc);
                <#else>
                    ${var.type} ${var.name} = edge.get(${var.name}_enc);
                </#if>
            </#if>
        </#list>

        <#list priorityStatements as stmt>
        if (${stmt.condition}) {
            return ${stmt.value};
        }
        </#list>
        return super.getPriority(edge, reverse);
    }

    @Override
    public double getSpeed(EdgeIteratorState edge, boolean reverse) {
        <#list speedStatements as stmt>
        if (${stmt.condition}) {
            return ${stmt.value};
        }
        </#list>
        return super.getSpeed(edge, reverse);
    }


    private PreparedPolygon createAreaPolygon(String id, Map<String, JsonFeature> areas) {
        JsonFeature feature = areas.get(id);
        if (feature == null) throw new IllegalArgumentException("Area '" + id + "' not found");
        return new PreparedPolygon((Polygonal) feature.getGeometry());
    }
}
