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
            <#if var.isEnum>
                private EnumEncodedValue<${var.type}> ${var.name}_enc;
            <#else>
                private ${var.type} ${var.name}_enc;
            </#if>
        </#if>
    </#list>

    // Special handling for OSM ID
    private IntEncodedValue osm_id_enc;

    @Override
    public void init(CustomModel customModel, EncodedValueLookup lookup, Map<String, JsonFeature> areas) {
        super.init(customModel, lookup, areas);
        <#list variables as var>
            <#if var.isArea>
                this.${var.name} = createAreaPolygon("${var.name?replace("in_", "")}", areas);
            <#else>
                try {
                    <#if var.isEnum>
                        this.${var.name}_enc = lookup.getEncodedValue("${var.name}", EnumEncodedValue.class);
                    <#else>
                        this.${var.name}_enc = lookup.getEncodedValue("${var.name}", ${var.type}.class);
                    </#if>
                } catch (IllegalArgumentException e) {
                    // Skip if the encoded value is not available
                    this.${var.name}_enc = null;
                }
            </#if>
        </#list>

        // Special initialization for OSM ID
        try {
            this.osm_id_enc = lookup.getIntEncodedValue("osm_id");
        } catch (IllegalArgumentException e) {
            this.osm_id_enc = null;
        }
    }

    @Override
    public double getPriority(EdgeIteratorState edge, boolean reverse) {
        // Add variable declarations
        <#list variables as var>
            <#if !var.isArea && var.name != "osm_id" && var.name != "edge_id">
                <#if var.isEnum>
                    ${var.type} ${var.name} = ${var.name}_enc != null ? edge.get(${var.name}_enc) : null;
                <#elseif var.type == "BooleanEncodedValue">
                    boolean ${var.name} = ${var.name}_enc != null ? edge.get(${var.name}_enc) : false;
                <#elseif var.type == "DecimalEncodedValue">
                    double ${var.name} = ${var.name}_enc != null ? edge.get(${var.name}_enc) : 0;
                <#elseif var.type == "IntEncodedValue">
                    int ${var.name} = ${var.name}_enc != null ? edge.get(${var.name}_enc) : 0;
                <#else>
                    ${var.type} ${var.name} = ${var.name}_enc != null ? edge.get(${var.name}_enc) : null;
                </#if>
            </#if>
        </#list>

        // Special handling for OSM ID
        int osm_id = osm_id_enc != null ? edge.get(osm_id_enc) : 0;

        <#list priorityStatements as stmt>
        if (${stmt.condition}) {
            return ${stmt.value};
        }
        </#list>
        return super.getPriority(edge, reverse);
    }

    @Override
    public double getSpeed(EdgeIteratorState edge, boolean reverse) {
        // Add variable declarations (same as getPriority)
        <#list variables as var>
            <#if !var.isArea && var.name != "osm_id" && var.name != "edge_id">
                <#if var.isEnum>
                    ${var.type} ${var.name} = ${var.name}_enc != null ? edge.get(${var.name}_enc) : null;
                <#elseif var.type == "BooleanEncodedValue">
                    boolean ${var.name} = ${var.name}_enc != null ? edge.get(${var.name}_enc) : false;
                <#elseif var.type == "DecimalEncodedValue">
                    double ${var.name} = ${var.name}_enc != null ? edge.get(${var.name}_enc) : 0;
                <#elseif var.type == "IntEncodedValue">
                    int ${var.name} = ${var.name}_enc != null ? edge.get(${var.name}_enc) : 0;
                <#else>
                    ${var.type} ${var.name} = ${var.name}_enc != null ? edge.get(${var.name}_enc) : null;
                </#if>
            </#if>
        </#list>

        // Special handling for OSM ID
        int osm_id = osm_id_enc != null ? edge.get(osm_id_enc) : 0;

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
