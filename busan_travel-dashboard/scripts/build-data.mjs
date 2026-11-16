/**
 * 부산 공공데이터(TourAPI 4.0) 원본 JSON → BusanPlace[] 정규화
 * 원본 스키마: public/data/SCHEMA.md, 출처: public/data/SOURCE.md
 *
 * 실행: npm run build:data
 * 출력: public/data/spots.json (festival 제외 7종), public/data/festivals.json (festival)
 */
import { readFile, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DATA_DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'public', 'data');

/** contentTypeId → BusanPlace.category (SCHEMA.md 코드 테이블 참고) */
const CATEGORY_BY_CONTENT_TYPE_ID = {
    12: 'attraction',
    14: 'culture',
    15: 'festival',
    25: 'course',
    28: 'leports',
    32: 'lodging',
    38: 'shopping',
    39: 'restaurant',
};

const SOURCE_FILES = [
    '부산_관광지.json',
    '부산_레포츠.json',
    '부산_문화시설.json',
    '부산_쇼핑.json',
    '부산_숙박.json',
    '부산_여행코스.json',
    '부산_음식점.json',
    '부산_축제공연행사.json',
];

/**
 * 원본 TourAPI item 1건을 BusanPlace로 정규화. 필수값(좌표/이름)이 없으면 null 반환.
 * @param {Record<string, string>} item
 * @param {string} contentType - 원본 파일의 contentType 한글명 (tags 채우는 용도)
 * @returns {import('../src/type.js').BusanPlace | null}
 */
function normalizeItem(item, contentType) {
    const category = CATEGORY_BY_CONTENT_TYPE_ID[Number(item.contenttypeid)];
    const name = item.title?.trim();
    const lat = Number.parseFloat(item.mapy);
    const lng = Number.parseFloat(item.mapx);

    if (!category || !name || !item.contentid || Number.isNaN(lat) || Number.isNaN(lng)) {
        return null;
    }

    const address = [item.addr1, item.addr2].filter(Boolean).join(' ').trim();

    return {
        id: item.contentid,
        name,
        category,
        address,
        lat,
        lng,
        description: '',
        tags: [contentType],
    };
}

async function loadRawFile(filename) {
    const filePath = path.join(DATA_DIR, filename);
    if (!existsSync(filePath)) {
        console.warn(`[build-data] 건너뜀 - 파일 없음: ${filename}`);
        return null;
    }
    const raw = JSON.parse(await readFile(filePath, 'utf-8'));
    return raw;
}

async function main() {
    const spots = [];
    const festivals = [];
    let skipped = 0;

    for (const filename of SOURCE_FILES) {
        const raw = await loadRawFile(filename);
        if (!raw) continue;

        for (const item of raw.items ?? []) {
            const place = normalizeItem(item, raw.contentType);
            if (!place) {
                skipped += 1;
                continue;
            }
            (place.category === 'festival' ? festivals : spots).push(place);
        }
    }

    await writeFile(path.join(DATA_DIR, 'spots.json'), JSON.stringify(spots, null, 2) + '\n', 'utf-8');
    await writeFile(path.join(DATA_DIR, 'festivals.json'), JSON.stringify(festivals, null, 2) + '\n', 'utf-8');

    console.log(`[build-data] spots.json: ${spots.length}건, festivals.json: ${festivals.length}건, 스킵: ${skipped}건`);
}

main();
