window.dashExtensions = Object.assign({}, window.dashExtensions, {
  default: {
    geojsonOnEachFeature: function (feature, layer, context) {
      const moisture = feature.properties.soil_moisture.toFixed(3);
      const coordinates = feature.geometry.coordinates;
      const unit = feature.properties.unit;
      const has_uncertainty = feature.properties.has_uncertainty;
      if (has_uncertainty) {
        const uncertainty_high = feature.properties.uncertainty_high;
        const uncertainty_low = feature.properties.uncertainty_low;
        layer.bindTooltip(
          `Soil Moisture: ${moisture} ${unit} (-${uncertainty_low}, +${uncertainty_high})<br>Coordinates: [${coordinates[1].toFixed(3)}, ${coordinates[0].toFixed(3)}]`,
          { sticky: true },
        );
        return;
      }
      layer.bindTooltip(
        `Soil Moisture: ${moisture} ${unit}<br>Coordinates: [${coordinates[1].toFixed(3)}, ${coordinates[0].toFixed(3)}]`,
        { sticky: true },
      );
    },
    geojsonPointToLayer: function (feature, latlng, context) {
      const { min, max, colorscale, circleOptions, colorProp } =
        context.hideout;
      const csc = chroma.scale(colorscale).domain([min, max]);

      // Use radius from feature properties if available, otherwise use default
      const radius =
        feature.properties.radius !== undefined
          ? feature.properties.radius
          : circleOptions.radius;

      circleOptions.fillColor = csc(feature.properties[colorProp]);
      circleOptions.radius = radius;

      return L.circleMarker(latlng, circleOptions);
    },
  },
});
