-- Resolve image nodes and explicit SVG companion links; leave other links unchanged.
local map_path = os.getenv('SAPOTE_PDF_RESOURCE_MAP')
if not map_path then error('PDF_RESOURCE_MAP_MISSING') end
local handle = assert(io.open(map_path, 'r'))
local mapping = pandoc.json.decode(handle:read('*a'))
handle:close()
if mapping.schema ~= 'sapote_pdf_image_map_v1' or type(mapping.targets) ~= 'table' then
  error('PDF_RESOURCE_MAP_INVALID')
end

local function safe_html_comment(value)
  local _, openings = value:gsub('<!%-%-', '')
  local _, closings = value:gsub('%-%->', '')
  return value:sub(1, 4) == '<!--' and value:sub(-3) == '-->'
      and openings == 1 and closings == 1
end

local function refuse_unless_comment(el)
  if tostring(el.format) == 'html' and safe_html_comment(el.text) then return end
  error('PDF_RAW_IMAGE_RESOURCE_REFUSED')
end

function Image(el)
  local target = mapping.targets[el.src]
  if not target then error('PDF_IMAGE_UNMAPPED: ' .. el.src) end
  el.src = target
  return el
end

function Link(el)
  local companions = mapping.svg_companions or {}
  if pandoc.utils.stringify(el.content) == 'SVG version' and companions[el.target] then
    el.target = companions[el.target]
    return el
  end
end

function RawInline(el)
  refuse_unless_comment(el)
end

function RawBlock(el)
  refuse_unless_comment(el)
end

function Div(el)
  if el.attributes.style and el.attributes.style:lower():match('url%s*%(') then
    error('PDF_RAW_IMAGE_RESOURCE_REFUSED')
  end
end

function Span(el)
  if el.attributes.style and el.attributes.style:lower():match('url%s*%(') then
    error('PDF_RAW_IMAGE_RESOURCE_REFUSED')
  end
end
