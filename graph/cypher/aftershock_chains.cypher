:param minMainshockMagnitude => 5.5;
:param minChainEvents => 3;
:param limit => 25;

// Assumes relationship direction:
// (:Earthquake aftershock)-[:AFTERSHOCK_OF]->(:Earthquake mainshock)

MATCH p = (main:Earthquake)<-[:AFTERSHOCK_OF*1..5]-(tail:Earthquake)
WHERE main.magnitude >= $minMainshockMagnitude
  AND NOT (main)-[:AFTERSHOCK_OF]->(:Earthquake)
WITH
  p,
  main,
  tail,
  nodes(p) AS events,
  relationships(p) AS links
WHERE size(events) >= $minChainEvents
  AND all(i IN range(0, size(events) - 2)
          WHERE events[i].time < events[i + 1].time)
WITH
  main,
  tail,
  events,
  links,
  size(links) AS chain_depth,
  reduce(total = 0.0, r IN links | total + r.time_delta_days) AS cumulative_lag_days,
  reduce(total = 0.0, r IN links | total + r.dist_km) / size(links) AS avg_step_distance_km,
  [e IN events | {
    event_id: e.event_id,
    time: e.time,
    magnitude: e.magnitude,
    depth_km: e.depth_km,
    place: e.place
  }] AS chain
RETURN
  main.event_id AS mainshock_id,
  main.time AS mainshock_time,
  main.magnitude AS mainshock_magnitude,
  main.place AS mainshock_place,
  tail.event_id AS terminal_aftershock_id,
  tail.time AS terminal_aftershock_time,
  tail.magnitude AS terminal_aftershock_magnitude,
  chain_depth,
  cumulative_lag_days,
  avg_step_distance_km,
  chain
ORDER BY chain_depth DESC, mainshock_magnitude DESC, cumulative_lag_days DESC
LIMIT $limit;