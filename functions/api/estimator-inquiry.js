const BASIN_ENDPOINT = 'https://usebasin.com/f/7e871e35a6e1';
const MAX_REQUEST_BYTES = 64 * 1024;

const ALLOWED = {
  tier: new Set(['functional', 'premium', 'custom']),
  strengthPackage: new Set(['none', 'dumbbells', 'rack', 'complete']),
  flooring: new Set(['performance', 'tile', 'designer']),
  mirrors: new Set(['none', 'single', 'wraparound']),
  lighting: new Set(['existing', 'upgraded', 'statement']),
  walls: new Set(['paint', 'accent', 'designer']),
  recovery: new Set([
    'sauna_prefab', 'sauna_custom', 'coldplunge_prefab', 'coldplunge_custom',
    'redlight', 'toolcharging', 'massageroom'
  ])
};

const RECOVERY_LABELS = {
  sauna_prefab: 'Sauna — Prefab',
  sauna_custom: 'Sauna — Custom',
  coldplunge_prefab: 'Cold Plunge — Prefab',
  coldplunge_custom: 'Cold Plunge — Custom',
  redlight: 'Red Light',
  toolcharging: 'Tool Charging Station',
  massageroom: 'Massage Room'
};

const LABELS = {
  tier: { functional: 'Functional equipment', premium: 'Premium equipment', custom: 'Custom & Signature equipment' },
  strengthPackage: { none: 'No dedicated strength package', dumbbells: 'Dumbbell set', rack: 'Rack / rig, with optional wall cable', complete: 'Dumbbells + rack / rig and wall cable' },
  flooring: { performance: 'Performance rubber flooring', tile: 'Premium tile flooring', designer: 'Designer flooring' },
  mirrors: { none: 'No mirrored walls', single: 'Single mirrored wall', wraparound: 'Wraparound mirrors' },
  lighting: { existing: 'Keep existing lighting', upgraded: 'Upgraded lighting', statement: 'Statement lighting' },
  walls: { paint: 'Paint refresh', accent: 'Accent wall', designer: 'Full designer wall treatment' }
};

const BASIS = 'Rounded planning allowances based on recent supplier pricing and historical equipment quotes. Design and procurement are included in the rounded equipment allowances. Final pricing depends on verified scope, availability, delivery, installation, taxes, and site conditions.';

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-store, max-age=0',
      'X-Content-Type-Options': 'nosniff'
    }
  });
}

function finiteRange(value) {
  return value && Number.isFinite(value.low) && Number.isFinite(value.high) &&
    value.low >= 0 && value.high >= value.low;
}

function loadBands(raw) {
  // Store the rate table as an encrypted Pages Function secret, never in public page code.
  if (typeof raw !== 'string' || !raw.trim()) return null;
  try {
    const bands = JSON.parse(raw);
    if (!bands || !bands.cardio || !bands.cardioLogistics || !bands.strength || !bands.flooring) return null;
    if (!['functional', 'premium', 'custom'].every(key => finiteRange(bands.cardio[key]))) return null;
    if (!finiteRange(bands.cardioLogistics)) return null;
    if (!['none', 'dumbbells', 'rack', 'complete'].every(key => finiteRange(bands.strength[key]))) return null;
    if (!['performance', 'tile'].every(key => {
      const value = bands.flooring[key];
      return value && Number.isFinite(value.lowPerSqFt) && Number.isFinite(value.highPerSqFt) &&
        value.lowPerSqFt >= 0 && value.highPerSqFt >= value.lowPerSqFt;
    })) return null;
    return bands;
  } catch {
    return null;
  }
}

function validPlan(plan) {
  if (!plan || typeof plan !== 'object' || Array.isArray(plan)) return false;
  if (!Number.isInteger(plan.sqft) || plan.sqft < 200 || plan.sqft > 1500 || (plan.sqft - 200) % 25 !== 0) return false;
  if (!ALLOWED.tier.has(plan.tier) || !ALLOWED.strengthPackage.has(plan.strengthPackage)) return false;
  if (!Number.isInteger(plan.cardioCount) || plan.cardioCount < 0 || plan.cardioCount > 6) return false;
  if (!ALLOWED.flooring.has(plan.flooring) || !ALLOWED.mirrors.has(plan.mirrors) ||
      !ALLOWED.lighting.has(plan.lighting) || !ALLOWED.walls.has(plan.walls)) return false;
  return Array.isArray(plan.recovery) && plan.recovery.length <= ALLOWED.recovery.size &&
    new Set(plan.recovery).size === plan.recovery.length &&
    plan.recovery.every(item => ALLOWED.recovery.has(item));
}

function floorThousand(value) {
  return Math.floor(value / 1000) * 1000;
}

function ceilThousand(value) {
  return Math.ceil(value / 1000) * 1000;
}

function calculateEstimate(plan, bands) {
  const lines = [];
  const notes = [];

  if (plan.cardioCount > 0) {
    const range = bands.cardio[plan.tier];
    const low = (range.low + bands.cardioLogistics.low) * plan.cardioCount;
    const high = (range.high + bands.cardioLogistics.high) * plan.cardioCount;
    lines.push({ label: `Cardio equipment (${plan.cardioCount})`, low: floorThousand(low), high: ceilThousand(high) });
    notes.push('Cardio includes a delivery / logistics allowance; final equipment selection and installation are confirmed during design.');
  }

  if (plan.strengthPackage !== 'none') {
    const range = bands.strength[plan.strengthPackage];
    lines.push({ label: LABELS.strengthPackage[plan.strengthPackage], low: floorThousand(range.low), high: ceilThousand(range.high) });
    notes.push('Strength equipment shipping and installation are not included in that allowance.');
  }

  if (plan.flooring === 'performance' || plan.flooring === 'tile') {
    const rate = bands.flooring[plan.flooring];
    lines.push({
      label: `${LABELS.flooring[plan.flooring]} (${plan.sqft.toLocaleString('en-US')} sq ft)`,
      low: floorThousand(rate.lowPerSqFt * plan.sqft),
      high: ceilThousand(rate.highPerSqFt * plan.sqft)
    });
    notes.push('Flooring is a material planning allowance; subfloor preparation, transitions, freight, and installation vary by site.');
  } else {
    notes.push('Designer flooring requires a project-specific quote and is not included in the priced range.');
  }

  if (plan.mirrors !== 'none') notes.push('Mirrors are not included in the priced range and require a project-specific measure and quote.');
  if (plan.lighting !== 'existing') notes.push('Lighting upgrades are not included in the priced range and depend on the existing electrical and ceiling conditions.');
  if (plan.walls !== 'paint') notes.push('Accent and designer wall finishes are not included in the priced range and require project-specific material and installation pricing.');
  if (plan.recovery.length) notes.push('Recovery, wellness, and dedicated service-room selections are not included in the priced range and require project-specific pricing.');

  notes.push('Taxes, construction, structural work, and unselected or unpriced custom scope are excluded.');
  const available = lines.length > 0;
  return {
    available,
    low: available ? lines.reduce((sum, item) => sum + item.low, 0) : null,
    high: available ? lines.reduce((sum, item) => sum + item.high, 0) : null,
    lines,
    notes,
    basis: BASIS
  };
}

function selectionsFor(plan) {
  return [
    `Space: ${plan.sqft.toLocaleString('en-US')} sq ft`,
    `Equipment tier: ${LABELS.tier[plan.tier]}`,
    `Cardio: ${plan.cardioCount} ${plan.cardioCount === 1 ? 'piece' : 'pieces'}`,
    `Strength: ${LABELS.strengthPackage[plan.strengthPackage]}`,
    `Flooring: ${LABELS.flooring[plan.flooring]}`,
    `Mirrors: ${LABELS.mirrors[plan.mirrors]}`,
    `Lighting: ${LABELS.lighting[plan.lighting]}`,
    `Wall finish: ${LABELS.walls[plan.walls]}`,
    `Recovery: ${plan.recovery.map(item => RECOVERY_LABELS[item]).join(', ') || 'None selected'}`
  ].join('\n');
}

function estimateFields(estimate) {
  const range = estimate.available ? `$${estimate.low.toLocaleString('en-US')} – $${estimate.high.toLocaleString('en-US')}` : 'No verified priced scope selected';
  const breakdown = estimate.lines.length
    ? estimate.lines.map(item => `${item.label}: $${item.low.toLocaleString('en-US')} – $${item.high.toLocaleString('en-US')}`).join('\n')
    : 'No priced selections.';
  return { range, breakdown };
}

function validLead(fields) {
  const text = key => {
    const value = fields.get(key);
    return typeof value === 'string' ? value.trim() : '';
  };
  const firstName = text('firstName');
  const lastName = text('lastName');
  const email = text('email');
  const phone = text('phone');
  const projectType = fields.get('projectType');
  const budget = text('budget');
  const timeline = text('timeline');
  const vision = text('vision');
  return firstName.length > 0 && firstName.length <= 100 &&
    lastName.length > 0 && lastName.length <= 100 &&
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) && email.length <= 254 &&
    phone.length > 6 && phone.length <= 60 && projectType === 'residence' &&
    budget.length > 0 && budget.length <= 100 && timeline.length > 0 && timeline.length <= 100 &&
    vision.length >= 20 && vision.length <= 5000 && fields.get('source') === 'estimator';
}

export async function onRequestPost({ request, env }) {
  const origin = request.headers.get('Origin');
  let requestOrigin;
  try {
    requestOrigin = new URL(request.url).origin;
  } catch {
    return json({ success: false, error: 'Invalid request.' }, 400);
  }
  if (!origin || origin !== requestOrigin) return json({ success: false, error: 'Request origin was not accepted.' }, 403);
  if (!request.headers.get('Content-Type')?.toLowerCase().startsWith('multipart/form-data;')) {
    return json({ success: false, error: 'Expected a form submission.' }, 415);
  }
  const declaredLength = Number(request.headers.get('Content-Length') || 0);
  if (declaredLength > MAX_REQUEST_BYTES) return json({ success: false, error: 'Form is too large.' }, 413);
  try {
    const actualLength = (await request.clone().arrayBuffer()).byteLength;
    if (actualLength > MAX_REQUEST_BYTES) return json({ success: false, error: 'Form is too large.' }, 413);
  } catch {
    return json({ success: false, error: 'Could not read form submission.' }, 400);
  }

  const bands = loadBands(env?.MFE_ESTIMATOR_BANDS);
  if (!bands) return json({ success: false, error: 'Estimator pricing is not configured.' }, 503);

  let fields;
  try {
    fields = await request.formData();
  } catch {
    return json({ success: false, error: 'Could not read form submission.' }, 400);
  }
  if (!validLead(fields)) return json({ success: false, error: 'Please complete all required inquiry fields.' }, 400);

  const rawPlan = fields.get('estimator_plan');
  let plan;
  try {
    if (typeof rawPlan !== 'string' || rawPlan.length > 4000) throw new Error('Invalid plan.');
    plan = JSON.parse(rawPlan);
  } catch {
    return json({ success: false, error: 'Planner selections were invalid.' }, 400);
  }
  if (!validPlan(plan)) return json({ success: false, error: 'Planner selections were invalid.' }, 400);

  const estimate = calculateEstimate(plan, bands);
  const { range, breakdown } = estimateFields(estimate);
  const basinFields = new FormData();
  const serverOwned = new Set([
    'estimator_plan', 'estimator_range', 'estimator_breakdown',
    'estimator_scope_notes', 'estimator_basis', 'estimator_selections', '_subject'
  ]);
  for (const [key, value] of fields.entries()) {
    if (!serverOwned.has(key) && typeof value === 'string') basinFields.append(key, value);
  }
  basinFields.set('source', 'estimator');
  basinFields.set('_subject', 'New Gym Planning Tool Inquiry — Performance Edge');
  basinFields.set('estimator_selections', selectionsFor(plan));
  basinFields.set('estimator_range', range);
  basinFields.set('estimator_breakdown', breakdown);
  basinFields.set('estimator_scope_notes', estimate.notes.join('\n'));
  basinFields.set('estimator_basis', estimate.basis);

  let basinResponse;
  try {
    basinResponse = await fetch(BASIN_ENDPOINT, {
      method: 'POST',
      headers: { Accept: 'application/json' },
      body: basinFields
    });
  } catch {
    return json({ success: false, error: 'Inquiry service is temporarily unavailable.' }, 502);
  }
  if (!basinResponse.ok) return json({ success: false, error: 'Inquiry service did not accept the submission.' }, 502);
  return json({ success: true, estimate });
}
