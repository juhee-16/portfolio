/**
 * @typedef {Object} Post
 * @property {string} id
 * @property {string} title
 * @property {string} content
 * @property {string} author
 * @property {number} createdAt
 * @property {number} updatedAt
 * @property {number} viewCount
 * @property {string} imageUrl     - 이미지 URL
 * @property {string[]} tags       - 태그 목록
 */

/**
 * @typedef {'attraction'|'culture'|'festival'|'course'|'leports'|'lodging'|'shopping'|'restaurant'} BusanPlaceCategory
 * TourAPI contentTypeId 매핑: 12=attraction, 14=culture, 15=festival, 25=course, 28=leports, 32=lodging, 38=shopping, 39=restaurant
 */

/**
 * @typedef {Object} BusanPlace   - 부산 공공데이터 정규화 결과 (scripts/build-data.mjs 참고)
 * @property {string} id            - 원본 contentid
 * @property {string} name
 * @property {BusanPlaceCategory} category
 * @property {string} address
 * @property {number} lat
 * @property {number} lng
 * @property {string} description   - 원본 데이터에 설명 필드가 없어 현재는 항상 '' (추후 detailCommon2 API 연동 시 채움)
 * @property {string[]} tags        - 검색/필터용 키워드. 현재는 contentType 한글명 1개만 포함
 */

/**
 * @typedef {Object} ChatMessage
 * @property {string} id
 * @property {'user'|'assistant'} role
 * @property {string} content
 * @property {number} createdAt
 * @property {'sending'|'done'|'error'} status
 */